import sys

import asyncio

import base64
from io import BytesIO

from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.image as mpimg

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
                ivp1: f64s, ivp2: f64s, spp: f64s,
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
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp1 is not None else None 
    isivpon = ivp>0 if ivp is not None else None
    ivpon = ivp[isivpon] if isivpon is not None and isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    # ?Have power ( smartplug)
    issppon = spp>0 if spp is not None else None
    sppon = spp[issppon] if issppon is not None and issppon.any() else None
    sppon_mean = sppon.mean() if sppon is not None else 0
    sppon_max = sppon.max() if sppon is not None else 0

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
    timesppon = time[issppon] if issppon is not None  and issppon.any() else None
    timesbpbon = time[issbpbon] if issbpbon is not None and issbpbon.any() else None
    timesbpboff = time[issbpboff] if issbpboff is not None and issbpboff.any() else None
    timesbpoon = time[issbpoon] if issbpoon is not None and issbpoon.any() else None
    timesbpion = time[issbpion] if issbpion is not None and issbpion.any() else None
    timeon = timesppon if timesppon is not None else timeivpon if timeivpon is not None else timesbpion

    totals = smp.copy()
    if sppon is not None: 
        totals += spp    # 1.priority (smartplug)
        on600 = np.full_like(sppon,600) 
        on800 = np.full_like(sppon,800)
    elif ivpon is not None:
        totals += ivp    # 2.priority (inverter)
        on600 = np.full_like(ivpon, 600) 
        on800 = np.full_like(ivpon, 800)
    elif sbpoon is not None:
        totals += sbpo   # 3.priority (solarbank)        
        on600 = np.full_like(sbpion, 600)
        on800 = np.full_like(sbpion, 800) 
    slot_means = _power_means(time, totals, slots)


    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()
    
    if sppon is not None:
        logger.info(f'{__me__}: using smartplug samples only')
        
        ax.fill_between(time, 0, spp,
                        color='yellow',label='PLUG', lw=0, alpha=0.3)
        ax.fill_between(time, spp, spp  + smp,
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

        ax.fill_between(time[issbpion], 0, sbpo[issbpion],
                        color='yellow',label='BYPASS', alpha=0.3)
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
    if smpon is not None:
        title += f' House {smp[-1]:.0f}'
        title += f'={smp_mean:.0f}^{smp_max:.0f}W'

    if sppon is not None:
        title += f' | Plug {spp[-1]:.0f}'
        title += f'={sppon_mean:.0f}^{sppon_max:.0f}W'
    if ivpon is not None:
        title += f' | Inv {ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'
    if sbpoon is not None:
        title += f' | Bank {sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
          
    if sbpi is not None:
        title += f'\nSun {sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'
    if sbpb is not None:
        title += f' | Bat+ {-sbpbon[-1] if sbpb[-1] < 0 else 0:.0f}'
        title += f'={-sbpbon_mean:.0f}^{-sbpbon_min:.0f}W'
        #title += f' | Bat- {sbpboff[-1] if sbpb[-1] > 0 else 0:.0f}'
        #title += f'={sbpboff_mean:.0f}^{sbpboff_max:.0f}W'

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
                    ivp1: f64s, ivp2: f64s, spp: f64s,
                    sbpi: f64s, sbpo: f64s, sbpb: f64s, 
                    slots: timeslots = SLOTS):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_w_line,**vars()) # type: ignore[unused-ignore]
    else:
        return _get_w_line(**vars())


def _get_kwh_line(time: t64s, sme: f64s,
                  ive1: f64s, ive2: f64s, spe: f64s,
                  sbei: f64s, sbeo: f64s, sbeb: f64s, sbsb: f64s,
                  empty_kwh, full_kwh: f64s, price: f64, time_format: str = '%H:%Mh'):
    __me__ ='_get_kwh_line'

    logger.info(f'{__me__}: started')
    
    issmeon = sme>0 if sme is not None else None
    smeon = sme[issmeon] if issmeon is not None and issmeon.any() else None

    ive = ive1 + ive2 if ive1 is not None and ive1 is not None else None 
    isiveon = ive>0 if ive is not None else None
    iveon = ive[isiveon] if isiveon is not None and isiveon.any() else None

    isspeon = spe>0 if spe is not None else None
    speon = spe[isspeon] if isspeon is not None and isspeon.any() else None

    issbeoon = sbeo>0 if sbeo is not None else None
    sbeoon = sbeo[issbeoon] if issbeoon is not None and issbeoon.any() else None
    

    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if speon is not None:
        logger.info(f'{__me__}: using smartplug samples only')

        ax.fill_between(time, 0, spe,
                             color='yellow', label='PLUG',alpha=0.3)
        ax.fill_between(time, spe, spe + sme,
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
                             color='yellow', label='BANK',alpha=0.3)
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
            
    if speon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Plug {spe[-1]:.3f}kWh ~ {spe[-1]*price:.2f}€'
        else:
            title += f' | Plug {spe.sum():.3f}kWh ~ {spe.sum()*price:.2f}€'
    elif iveon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Inv {ive[-1]:.3f}kWh ~ {ive[-1]*price:.2f}€'
        else:
            title += f' | Inv {ive.sum():.3f}kWh ~ {ive.sum()*price:.2f}€'
    elif sbeoon is not None:
        if time_format == '%H:%Mh': # Accumulated
            title += f' | Bank {sbeo[-1]:.3f}kWh ~ {sbeo[-1]*price:.2f}€'
        else:
            title += f' | Bank {sbeo.sum():.3f}kWh ~ {sbeo.sum()*price:.2f}€'
        
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
                       ive1: f64s, ive2: f64s, spe: f64s,
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

    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if panelon is not None:
        logger.info(f'{__me__}: using unified samples')

        ax.bar(time, panel, bottom = 0,
               color='yellow', label='PANEL', width=bar_width, alpha=0.3)
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

