import sys

import asyncio

import base64
from io import BytesIO

from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches

import numpy as np

from typing import Any
from .types import f64, f64s, t64, t64s, timeslots


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)


XSIZE, YSIZE = 10, 5

SLOTS = ["00:00", "07:00", "10:00", "14:00", "17:00", "22:00", "23:59"]


def _hm2date(value: str) -> t64:
    dt = datetime.strptime(value,"%H:%M")
    return t64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

def _power_means(times: t64s,
                 powers: f64s,
                 slots: timeslots) -> f64s:
    spowers = np.full_like(powers, 0.0)
    for start, stop in zip(slots[:-1], slots[1:]):
        wheres, = np.where((times >= _hm2date(start)) & (times <= _hm2date(stop)))
        spowers[wheres] = powers[wheres].mean() if wheres.size > 0 else None
    return spowers


def _get_w_line(time: t64s, smp: f64s,
                ivp1: f64s, ivp2: f64s, spph: f64s,
                sbpi: f64s, sbpo: f64s, sbpb: f64s,
                slots: timeslots = SLOTS):
    __me__ ='_get_w_line'

    logger.info(f'{__me__}: started')

    # ?Have data (smartmeter)
    issmpon = smp>0 if smp is not None else None 
    smpon = smp[issmpon] if issmpon  is not None and issmpon.any() else None
    smp_mean = smpon.mean() if smpon is not None else 0
    smp_max = smpon.max() if smpon is not None else 0

    # ?Have data (inverter)
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp2 is not None else None 
    isivpon = ivp>0 if ivp is not None else None
    ivpon = ivp[isivpon] if isivpon is not None and isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    # ?Have power ( smartplug)
    isspphon = spph>0 if spph is not None else None
    spphon = spph[isspphon] if isspphon is not None and isspphon.any() else None
    spphon_mean = spphon.mean() if spphon is not None else 0
    spphon_max = spphon.max() if spphon is not None else 0

    # ?Have sun (solarbank)
    issbpion = sbpi>0  if sbpi is not None else None
    sbpion = sbpi[issbpion] if issbpion is not None and issbpion.any() else None
    sbpion_mean = sbpion.mean() if sbpion is not None else 0
    sbpion_max = sbpion.max() if sbpion is not None else 0

    # 'Have output (solarbank)
    issbpoon = sbpo>0 if sbpo is not None else None 
    sbpoon = sbpo[issbpoon] if issbpoon is not None and issbpoon.any() else None
    sbpoon_mean = sbpoon.mean() if sbpoon is not None else 0
    sbpoon_max = sbpoon.max() if sbpoon is not None else 0

    # ?Charging (solarbank)
    issbpbon = sbpb<0 if sbpb is not None else None 
    sbpbon = sbpb[issbpbon] if issbpbon is not None and issbpbon.any() else None
    sbpbon_mean = sbpbon.mean() if sbpbon is not None else 0
    sbpbon_min = sbpbon.min() if sbpbon is not None else 0

    # ?Discharging (solarbank)
    issbpboff = sbpb>0 if sbpb is not None else None  
    sbpboff = sbpb[issbpboff] if issbpboff is not None and issbpboff.any() else None
    sbpboff_mean = sbpboff.mean() if sbpboff is not None else 0
    sbpboff_max = sbpboff.max() if sbpboff is not None else 0
    
    timeivpon = time[isivpon] if isivpon is not None and isivpon.any() else None
    timespphon = time[isspphon] if isspphon is not None  and isspphon.any() else None
    timesbpbon = time[issbpbon] if issbpbon is not None and issbpbon.any() else None
    timesbpboff = time[issbpboff] if issbpboff is not None and issbpboff.any() else None
    timesbpoon = time[issbpoon] if issbpoon is not None and issbpoon.any() else None
    timesbpion = time[issbpion] if issbpion is not None and issbpion.any() else None
    timeon = timespphon if timespphon is not None else timeivpon if timeivpon is not None else timesbpion

    totals = smp.copy()
    if spphon is not None: 
        totals += spph    # 1.priority (smartplug)
        on600 = np.full_like(spphon,600) 
        on800 = np.full_like(spphon,800)
    elif ivpon is not None:
        totals += ivp    # 2.priority (inverter)
        on600 = np.full_like(ivpon, 600) 
        on800 = np.full_like(ivpon, 800)
    elif sbpoon is not None:
        totals += sbpo   # 3.priority (solarbank)        
        on600 = np.full_like(sbpion, 600)
        on800 = np.full_like(sbpion, 800) 
    slot_means = _power_means(time, totals, slots)


    #plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()
    
    if spphon is not None:
        logger.info(f'{__me__}: using smartplug samples only')
        
        ax.fill_between(time, 0, spph,
                        color='grey',label='PLUG', lw=0, alpha=0.3)
        ax.fill_between(time, spph, spph  + smp,
                        color='b', label='HOUSE', lw=0, alpha=0.3)

        if ivpon is not None:
            ax.plot(time, ivp1,
                    color='c', lw=2, label='INV 1', alpha=0.6)
            ax.plot(time, ivp1 + ivp2,
                    color='g', lw=2, label='INV 2', alpha=0.6)

    elif ivpon is not None:
        logger.info(f'{__me__}: using inverter samples only')

        ax.fill_between(time, 0, ivp1,
                        color='c',label='INV 1', alpha=0.6)
        ax.fill_between(time, ivp1, ivp1 + ivp2,
                        color='g', label='INV 2', alpha=0.5)
        ax.fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smp,
                        color='b', label='HOUSE', alpha=0.3)

    elif sbpoon is not None:
        logger.info(f'{__me__}: using solarbank samples only')
        logger.warn(f'{__me__}: other power samples are ignored')

        ax.fill_between(time, 0, sbpo,
                        color='grey', label='BANK', alpha=0.3)
        ax.fill_between(time, sbpo, sbpo + smp,
                        color='b', label='HOUSE', alpha=0.3)

    elif smpon is not None:
        logger.info(f'{__me__}: using smartmeter samples only')
        logger.warn(f'{__me__}: other power samples are not provided')

        ax.fill_between(time, 0, smp,
                        color='b', label='HOUSE', lw=0, alpha=0.3)

        
    """ Plot the battery power of the solarbank during charging"""
    if sbpb is not None:
        """ The solarbank output is used directly in spite of inverter """
        ax.fill_between(time, 0, sbpb,
                        color='m', label='-BAT', lw=1, alpha=0.3)
        
    ax.plot(time, slot_means, 
            color='c', lw=2, ls='-', label="MEAN", alpha=0.4)

    if timeon is not None:
        ax.fill_between(timeon , on600, on800,
                        color='orange', label='LIMITS', alpha=0.4)

    title = f'# Power #\n'
    if sbpi is not None:
        title += f'Sun {sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'
    if sbpoon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Solix {sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
    if ivpon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Inv {ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'
    if smpon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'House {smp[-1]:.0f}'
        title += f'={smp_mean:.0f}^{smp_max:.0f}W'
    if spphon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug {spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'
        
    if sbpb is not None:
        title += f'\nBat+ {-sbpbon[-1] if sbpb[-1] < 0 else 0:.0f}'
        title += f'={-sbpbon_mean:.0f}^{-sbpbon_min:.0f}W'
        title += f' | Bat- {sbpboff[-1] if sbpb[-1] > 0 else 0:.0f}'
        title += f'={sbpboff_mean:.0f}^{sbpboff_max:.0f}W'

    ax.set_title(title)
    
    ax.legend(loc='lower left')
    ax.set_ylabel('Power [W]')
    ax.set_yscale('symlog')
    ax.xaxis_date()
    hm_formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(hm_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='both')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'{__me__}: done')

    return base64.b64encode(buf.getbuffer()).decode('ascii')


async def get_w_line(time: t64s, smp: f64s,
                    ivp1: f64s, ivp2: f64s, spph: f64s,
                    sbpi: f64s, sbpo: f64s, sbpb: f64s, 
                    slots: timeslots = SLOTS):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_w_line,**vars()) # type: ignore[unused-ignore]
    else:
        return _get_w_line(**vars())


def _get_kwh_line(time: t64s, sme: f64s,
                  ive1: f64s, ive2: f64s, speh: f64s,
                  sbei: f64s, sbeo: f64s, sbeb: f64s, sbsb: f64s,
                  empty_kwh, full_kwh: f64s, price: f64, time_format: str = '%H:%Mh'):
    __me__ ='_get_kwh_line'

    logger.info(f'{__me__}: started')
    
    issmeon = sme>0 if sme is not None else None
    smeon = sme[issmeon] if issmeon is not None and issmeon.any() else None

    ive = ive1 + ive2 if ive1 is not None and ive1 is not None else None 
    isiveon = ive>0 if ive is not None else None
    iveon = ive[isiveon] if isiveon is not None and isiveon.any() else None

    isspehon = speh>0 if speh is not None else None
    spehon = speh[isspehon] if isspehon is not None and isspehon.any() else None

    issbeoon = sbeo>0 if sbeo is not None else None
    sbeoon = sbeo[issbeoon] if issbeoon is not None and issbeoon.any() else None
    

    #plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if spehon is not None:
        logger.info(f'{__me__}: using smartplug samples only')

        ax.fill_between(time, 0, speh,
                             color='grey', label='PLUG',alpha=0.3)
        ax.fill_between(time, speh, speh + sme,
                             color='b',label='HOUSE', alpha=0.3)

    elif iveon is not None:
        logger.info(f'{__me__}: using inverter samples only')

        ax.fill_between(time, 0, ive1,
                             color='c', label='INV 1',alpha=0.6)
        ax.fill_between(time, ive1, ive2 + ive1,
                             color='g',label='INV 2', alpha=0.5)
        ax.fill_between(time, ive2 + ive1, ive2 + ive1 + sme,
                             color='b',label='HOUSE', alpha=0.3)

    elif sbeoon is not None:
        logger.info(f'{__me__}: using solarbank samples only')
        logger.warn(f'{__me__}: other energy samples are ignored')

        ax.fill_between(time, 0, sbeo,
                             color='grey', label='BANK',alpha=0.3)
        ax.fill_between(time, sbeo, sbeo + sme,
                             color='b',label='HOUSE', alpha=0.3)

    elif smeon is not None:
        logger.info(f'{__me__}: using smartmeter samples only')
        logger.warn(f'{__me__}: other energy samples are notprovided')

        ax.fill_between(time, sme,
                        color='b',label='HOUSE', alpha=0.3)

        
    if sbsb is not None:
        ax.fill_between(time, 0, -sbsb,
                        color='m', label='-BAT',alpha=0.3)

        ax.axhline(-empty_kwh, color='r', ls='--')        
        ax.axhline(-full_kwh, color='r', ls='--')

        
    title = f'# Energy #\n'
    if smeon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' House {sme[-1]:.1f}kWh ~ {(sme[-1]*price):.2f}€'
        else:
            title += f' House {sme.sum():.1f}kWh ~ {(sme.sum()*price):.2f}€'
            
    if spehon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Plug {speh[-1]:.1f}kWh ~ {speh[-1]*price:.2f}€'
        else:
            title += f' | Plug {speh.sum():.1f}kWh ~ {speh.sum()*price:.2f}€'
    elif iveon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Inv {ive[-1]:.1f}kWh ~ {ive[-1]*price:.2f}€'
        else:
            title += f' | Inv {ive.sum():.1f}kWh ~ {ive.sum()*price:.2f}€'
    elif sbeoon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Bank {sbeo[-1]:.1f}kWh ~ {sbeo[-1]*price:.2f}€'
        else:
            title += f' | Bank {sbeo.sum():.1f}kWh ~ {sbeo.sum()*price:.2f}€'
        
    if sbsb is not None:
        title += f' | Bat {sbsb[-1]*1000:.0f}Wh ~ {sbsb[-1]/full_kwh*100:.0f}%'
    
    ax.set_title(title)

    ax.legend(loc="upper left")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='both')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'{__me__}: done')

    return base64.b64encode(buf.getbuffer()).decode('ascii')

async def get_kwh_line(time: t64s, sme: f64s,
                       ive1: f64s, ive2: f64s, speh: f64s,
                       sbei: f64s, sbeo: f64s, sbeb: f64s, sbsb: f64s,
                       empty_kwh: f64s, full_kwh: f64s, price: f64,
                       time_format: str = '%H:%Mh'):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(_get_kwh_line, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_kwh_line(**vars())


def _get_kwh_bar_unified(
        time: t64s, sme: f64s, panel: f64,
        price: f64, bar_width: f64, time_format: str):

    __me__='_get_kwh_bar_unified'
    logger.info(f'{__me__}: started')

    smeon = sme[sme>0] if sme is not None else None
    panelon = panel[panel>0] if panel is not None else None

    #plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if panelon is not None:
        logger.info(f'{__me__}: using unified samples')

        ax.bar(time, panel, bottom = 0,
               color='grey', label='PANEL', width=bar_width, alpha=0.3)
        ax.bar(time, sme, bottom=panel,
               color='blue',label='HOUSE', width=bar_width, alpha=0.3)
        
        for x, ypanel, ysme, ytot in zip(time, panel, sme, panel + sme):
            if ypanel > 1.0:
                ax.text(x, ypanel/2, f'{ypanel:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysme > 1.0:
                ax.text(x, ysme/2 + ypanel, f'{ysme:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)

    elif smeon is not None:
        logger.info(f'{__me__}: using smartmeter samples only')

        ax.fill_between(time, sme,
                        color='b',label='HOUSE', alpha=0.3)
            
                
    title = f'Energy Check #'
    if smeon is not None:
        title += f' House {sme.sum():.1f}kWh ~ {(sme.sum()*price):.2f}€'   
    if panelon is not None:
        title += f' | Panel {panel.sum():.1f}kWh ~ {panel.sum()*price:.2f}€'

    ax.set_title(title, fontsize='x-large')

    ax.legend(loc="upper right")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='y')

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'{__me__}: done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')

async def get_kwh_bar_unified(
        time: t64s, sme: f64s, panel: f64s,
        price: f64, bar_width: f64, time_format:str):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_kwh_bar_unified, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_kwh_bar_unified(**vars())


def _get_blocks(time: t64, smp: f64,
                ivp1: f64, ivp2: f64, spph: f64,
                sbpi: f64, sbpo: f64, sbpb: f64,
                spp1: f64, spp2: f64):
    __me__ ='_blocks'

    logger.info(f'{__me__}: started')


    """ If the local mode does not work the inverter still works.To
    overcome solarbank output is assigned.  """
    if ivp1 + ivp2 <= 0:
        ivp1 = ivp2 = sbpo/2
        ivp = ivp1 + ivp2

    if np.isnan(ivp):
        ivp = 0

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.axis('equal')
    ax.axis('off')

    # Kann be anything! Only for relations
    BW, BH = 2, 2
    
    def _add_link_to_ax(ax: Any,
                        xb0: int, yb0: int, gate0: str,
                        xb1: int, yb1: int, gate1: str,
                        power: float, color: str) -> None:

        x = [None]*5
        x[0] = (2*xb0)*BW + (BW if gate0 in 'E' else -BW if gate0 in 'W' else 0)/2
        x[1] = x[0] + (BW if gate0 in 'E' else -BW if gate0 in 'W' else 0)/2
        x[4] = (2*xb1)*BW + (BW if gate1 in 'E' else -BW if gate1 in 'W' else 0)/2
        x[3] = x[4] + (BW if gate1 in 'E' else -BW if gate1 in 'W' else 0)/2
        x[2] = (x[1] + x[3])/2

        y = [None]*5
        y[0] = (2*yb0)*BH + (BH if gate0 in 'N' else -BH if gate0 in 'S' else 0)/2
        y[1] = y[0] + (BH if gate0 in 'N' else -BH if gate0 in 'S' else 0)/2
        y[4] = (2*yb1)*BH + (BH if gate1 in 'N' else -BH if gate1 in 'S' else 0)/2
        y[3] = y[4] + (BH if gate1 in 'N' else -BH if gate1 in 'S' else 0)/2
        y[2] = (y[1] + y[3])/2

        ha, va = 'center', 'center' if gate0 in "SN" and gate1 in "SN" else 'bottom'

        ltext = f'{power:.0f}W'
        lwidth = 2*np.log10(power)+1

        ax.plot(x, y, color=color, lw=lwidth, alpha=0.3)
        ax.annotate(ltext, (x[2], y[2]), color='black',
                    weight='bold', fontsize=9, ha=ha, va=va, alpha=0.9)
                

    def _add_box_to_ax(ax: Any, xb: int, yb: int, text: str, color: str) -> None:
        x, y = (2*xb)*BW-BW/2, (2*yb)*BH-BH/2
        r = mpatches.Rectangle((x, y), BW, BH, facecolor=color,edgecolor='black',alpha=0.3)
        ax.add_patch(r)
        cx = x + r.get_width()/2.0
        cy = y + r.get_height()/2.0
        ax.annotate(text, (cx, cy), color='black', fontsize=9, ha='center', va='center')
        
    panel_1 = (0,  1)
    solix_mppt = (0,0)        
    panel_2 = (0, -1)
    solix_split = (1,0)        
    solix_bat = (1.5, 0.75)
    solix_out = (2, 0)
    inv_mppt_1 = (3,0.75)
    inv_mppt_2 = (3,-0.75)
    inv_out = (3,0)
    plugh = (3,0)
    house = (4,0)
    net = (4, 1)
    sinks = (4, -1)
    plug1 = (5 ,0.75)
    plug2 = (5.75 ,0.25)
    plug3 = (6.0 ,-0.5)
    plug4 = (5.75 ,-1.25)
        
    _add_box_to_ax(ax, *panel_1, 'PANEL 1', 'green')
    _add_box_to_ax(ax, *panel_2, 'PANEL 2', 'green')
    _add_box_to_ax(ax, *solix_mppt, 'SOLIX\nMPPT', 'grey')
    _add_box_to_ax(ax, *solix_split, 'SOLIX\nSPLIT', 'grey')
    _add_box_to_ax(ax, *solix_out, 'SOLIX\nOUT', 'grey')
    _add_box_to_ax(ax, *solix_bat, 'SOLIX\nBAT', 'grey')
    _add_box_to_ax(ax, *house, 'METER\nHOUSE',
                   'blue' if smp>0 else 'magenta' if sbpb>0 else 'grey')
    _add_box_to_ax(ax, *net, 'POWER\nNET', 'blue')
    _add_box_to_ax(ax, *inv_mppt_1, 'INV\nMPPT 1', 'cyan')
    _add_box_to_ax(ax, *inv_mppt_2, 'INV\nMPPT 2', 'cyan')
    if spph > 0:
        _add_box_to_ax(ax, *plugh, 'PLUG\nHOUSE', 'brown')
    else:
        _add_box_to_ax(ax, *inv_out, 'INV\nOUT', 'cyan')
    _add_box_to_ax(ax, *sinks, 'MANY\nSINKS',
                   'blue' if smp>0 else 'magenta' if sbpb>0 else 'grey')
    _add_box_to_ax(ax, *plug1, 'PLUG 1\nSINK',
                   'blue' if smp>0 and spp1>0 else 'magenta' if sbpb>0 and spp1>0 else 'white')
    _add_box_to_ax(ax, *plug2, 'PLUG 2\nSINK',
                   'blue' if smp>0 and spp2>0 else 'magenta' if sbpb>0 and spp2>0 else 'white')
    spp3=spp4=0 #TODO
    _add_box_to_ax(ax, *plug3, 'PLUG 3\nSINK',
                   'blue' if smp>0 and spp3>0 else 'magenta' if sbpb>0 and spp3>0 else 'white')
    _add_box_to_ax(ax, *plug4, 'PLUG 4\nSINK',
                   'blue' if smp>0 and spp3>0 else 'magenta' if sbpb>0 and spp4>0 else 'white')
    

    if sbpi>0 :
        _add_link_to_ax(ax, *panel_1, 'S', *solix_mppt, 'N',
                    sbpi/2, 'green')
        _add_link_to_ax(ax, *panel_2, 'N', *solix_mppt, 'S',
                    sbpi/2, 'green')
        _add_link_to_ax(ax, *solix_mppt, 'E', *solix_split, 'W',
                        sbpi, 'grey')

    if sbpb<0 :
        _add_link_to_ax(ax, *solix_split, 'N', *solix_bat, 'W',
                        -sbpb, 'm')
    
    if sbpb>0 :
        _add_link_to_ax(ax, *solix_bat, 'E', *solix_out, 'N',
                        sbpb, 'm')
    if sbpi > 0:
        _add_link_to_ax(ax, *solix_split, 'S', *solix_out, 'S',
                        sbpi+sbpb, 'grey')
    if ivp1 > 0:
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_1, 'W',
                        ivp1, 'magenta' if sbpb>0 else 'grey')
        if spph>0:
            _add_link_to_ax(ax, *inv_mppt_1, 'S', *plugh, 'N',
                            ivp1, 'magenta' if sbpb>0 else 'grey')
        else:
            _add_link_to_ax(ax, *inv_mppt_1, 'S', *inv_out, 'N',
                            ivp1, 'magenta' if sbpb>0 else 'grey')
    if ivp2 > 0:
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_2, 'W',
                        ivp2, 'magenta' if sbpb>0 else 'grey')
        if spph>0:
            _add_link_to_ax(ax, *inv_mppt_2, 'N', *plugh, 'S',
                            ivp1, 'magenta' if sbpb>0 else 'grey')
        else:
            _add_link_to_ax(ax, *inv_mppt_2, 'N', *inv_out, 'S',
                        ivp2, 'magenta' if sbpb>0 else 'grey')

    if spph > 0:
        _add_link_to_ax(ax, *plugh, 'E', *house, 'W',
                        spph, 'magenta' if sbpb>0 else 'grey')
    elif ivp > 0:
        _add_link_to_ax(ax, *inv_out, 'E', *house, 'W',
                        ivp, 'magenta' if sbpb>0 else 'grey')

    if smp > 0:
        _add_link_to_ax(ax, *net, 'S', *house, 'N', smp, 'blue')
        _add_link_to_ax(ax, *house, 'S', *sinks, 'N',
                        smp + (spph if spph>0 else ivp), 'brown')
    else:
        _add_link_to_ax(ax, *house, 'S', *sinks, 'N',
                        spph if spph>0 else ivp, 'brown')

    if spp1>0:
        _add_link_to_ax(ax, *sinks, 'E', *plug1, 'W', spp1, 'brown')
    if spp2>0:
        _add_link_to_ax(ax, *sinks, 'E', *plug2, 'W', spp2, 'brown')
    if spp3>0:
        _add_link_to_ax(ax, *sinks, 'E', *plug3, 'W', spp3, 'brown')
    if spp4>0:
        _add_link_to_ax(ax, *sinks, 'E', *plug4, 'W', spp4, 'brown')

    _add_link_to_ax(ax, *sinks, 'S', *sinks, 'S',
                    smp + (spph if spph>0 else ivp)-spp1-spp2-spp3-spp4, 'brown')
        
    title = f'# System #'
    title += f'\nLast Sample of the Day'
    ax.set_title(title)
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'{__me__}: done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')

async def get_blocks(time: t64, smp: f64,
                     ivp1: f64, ivp2: f64, spph: f64,
                     sbpi: f64s, sbpo: f64s, sbpb: f64,
                     spp1: f64, spp2: f64):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_w_line,**vars()) # type: ignore[unused-ignore]
    else:
        return _get_blocks(**vars())
