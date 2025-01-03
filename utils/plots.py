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
from .types import f64, f64s, t64, t64s


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)


XSIZE, YSIZE = 10, 5


def _get_w_line(time: t64s, smp: f64s,
                ivp1: f64s, ivp2: f64s, spph: f64s,
                sbpi: f64s, sbpo: f64s, sbpb: f64s,
                tphases: t64s = None):
    __me__ ='_get_w_line'

    logger.info(f'{__me__}: started')

    # ?Have data (smartmeter)
    smpon = np.zeros_like(smp)
    issmpon = smp>0 if smp is not None else None
    smpon[issmpon] = smp[issmpon] 
    smpon_mean = 0 if not issmpon.any() else smpon.mean()
    smpon_max = 0 if not issmpon.any() else smpon.max()

    smpoff = np.zeros_like(smp)
    issmpoff = smp<0 if smp is not None else None
    smpoff[issmpoff] = smp[issmpoff] 
    smpoff_mean = 0 if not issmpoff.any() else smpoff.mean()
    smpoff_min = 0 if not issmpoff.any() else smpoff.min()

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
    
    timesbpion = time[issbpion] if issbpion is not None else None
    timeivpon = time[isivpon] if issbpion is not None else None

    
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()

    if tphases is not None:
        ax.axvspan(tphases[0], tphases[1], 
                   color ='olive',
                   alpha = 0.2)        
        
    if spphon is not None:
        logger.info(f'{__me__}: using smartplug samples only')
        
        ax.fill_between(time, 0, spph,
                        color='grey',label='PLUG', lw=0, alpha=0.3)
        ax.fill_between(time, spph, spph + smpon,
                        color='b', label='GRID', lw=0, alpha=0.3)

        if ivpon is not None:
            ax.plot(time, ivp1,
                    color='c', lw=2, label='INV 1', alpha=0.6)
            ax.plot(time, ivp1 + ivp2,
                    color='g', lw=2, label='INV 2', alpha=0.6)

        #ax.plot(time, spph, color='black', label='<|>', lw=1, alpha=0.7)

    elif ivpon is not None:
        logger.info(f'{__me__}: using inverter samples only')
        
        ax.fill_between(time, 0, ivp1 + ivp2,
                        color='c', label='INV', alpha=0.2)
        ax.fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smpon,
                        color='b', label='GRID', alpha=0.3)

    elif sbpoon is not None:
        logger.info(f'{__me__}: using solarbank samples only')
        logger.warn(f'{__me__}: other power samples are ignored')

        ax.fill_between(time, 0, sbpo,
                        color='grey', label='BANK', lw=0, alpha=0.3)
        ax.fill_between(time, sbpo, sbpo + smpon,
                        color='b', label='GRID', lw=0, alpha=0.3)
        
    elif smpon is not None or smpoff is not None :
        logger.info(f'{__me__}: using smartmeter samples only')
        logger.warn(f'{__me__}: other power samples are not provided')

        ax.fill_between(time, 0, smp,
                        color='b', label='GRID', alpha=0.3)

        
    """ Plot the battery power of the solarbank during charging"""
    if sbpb is not None:
        """ The solarbank output is used directly inspite of inverter """
        ax.fill_between(time, 0, sbpb,
                        color='m', label='-BAT', alpha=0.3)
        sbpb_stacked = np.minimum(sbpb, [0])
        ax.fill_between(time, sbpb_stacked, sbpb_stacked + smpoff,
                        color='b', lw=0, alpha=0.3)

    else:
        ax.fill_between(time, 0, smpoff,
                        color='b', lw=0, alpha=0.3)
    
    if ivpon is not None:
        ax.fill_between(timeivpon ,
                        np.full_like(ivpon, 600),
                        np.full_like(ivpon, 800),
                        color='orange', label='LIMITS', alpha=0.4)

        
    title = f'# Power #\n'
    if sbpi is not None:
        title += f'Sun>{sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'

    if sbpoon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Bank>{sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
  
    if sbpb is not None:
        title += f' * {-sbpbon[-1] if sbpb[-1]<0 else 0:.0f}'
        title += f'={-sbpbon_mean:.0f}^{-sbpbon_min:.0f}W>'
        title += f'Bat'
        title += f'>{sbpboff[-1] if sbpb[-1]>0 else 0:.0f}'
        title += f'={sbpboff_mean:.0f}^{sbpboff_max:.0f}W'

    title += '' if title[-1] == '\n' else '\n'
        
    if ivpon is not None:
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'

    if spphon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug0>{spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'

    if smpon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'{-smp[-1] if smp[-1]<0 else 0:.0f}'
        title += f'={-smpoff_mean:.0f}^{-smpoff_min:.0f}W>'
        title += f'Grid'
        title += f'>{smp[-1] if smp[-1]>0 else 0:.0f}'
        title += f'={smpon_mean:.0f}^{smpon_max:.0f}W'
        
    ax.set_title(title)
    
    ax.legend(loc='upper left')
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
                     tphases: t64s = None):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_w_line,**vars()) # type: ignore[unused-ignore]
    else:
        return _get_w_line(**vars())


def _get_kwh_line(
        time: t64s, smeon: f64s, smeoff: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh, full_kwh: f64s, price: f64,
        tphases: t64s = None,
        time_format: str = '%H:%M'):
    __me__ ='_get_kwh_line'
    logger.info(f'{__me__}: started')

    ive = ive1 + ive2 if ive1 is not None and ive1 is not None else None 
    isiveon = ive>0 if ive is not None else None
    iveon = ive[isiveon] if isiveon is not None and isiveon.any() else None

    isspehon = speh>0 if speh is not None else None
    spehon = speh[isspehon] if isspehon is not None and isspehon.any() else None

    issbeion = sbei>0 if sbei is not None else None
    sbeion = sbei[issbeion] if issbeion is not None and issbeion.any() else None

    issbeoon = sbeo>0 if sbeo is not None else None
    sbeoon = sbeo[issbeoon] if issbeoon is not None and issbeoon.any() else None

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if tphases is not None:
        ax.axvspan(tphases[0], tphases[1], 
                   color ='olive',
                   alpha = 0.2)        

    if spehon is not None:
        logger.info(f'{__me__}: using smartplug samples only')

        ax.plot(time, smeoff, color='black', label='<|>', lw=1, alpha=0.7)
        
        ax.fill_between(time, 0, speh,
                             color='grey', label='PLUG',alpha=0.3)
        ax.fill_between(time, speh, speh + smeon,
                             color='b',label='GRID', alpha=0.3)

    elif iveon is not None:
        logger.info(f'{__me__}: using inverter samples only')

        ax.fill_between(time, 0, ive2 + ive1,
                             color='c',label='INV', alpha=0.3)                             
        ax.fill_between(time, ive2 + ive1, ive2 + ive1 + smeon,
                             color='b',label='GRID', alpha=0.3)

    elif sbeoon is not None:
        logger.info(f'{__me__}: using solarbank samples only')
        logger.warn(f'{__me__}: other energy samples are ignored')

        ax.fill_between(time, 0, sbeo,
                        color='grey', label='BANK',alpha=0.3)
        ax.fill_between(time, sbeo, sbeo + smeon,
                        color='b',label='GRID', alpha=0.3)

    elif smeon is not None:
        logger.info(f'{__me__}: using smartmeter samples only')
        logger.warn(f'{__me__}: other energy samples are notprovided')

        #ax.plot(time, smeoff, color='black', label='<|>', lw=1, alpha=0.7)

        ax.fill_between(time, smeoff, smeon,
                        color='b',label='GRID', alpha=0.3)

        
    if sbsb is not None:
        ax.axhline(-empty_kwh, color='r', ls='--')        
        ax.axhline(-full_kwh, color='r', ls='--')

        sbeb = +sbebcharge - sbebdischarge + sbsb[0]

        ax.fill_between(time, 0, -sbsb,
                        color='m', label='-BAT',alpha=0.3)

        ax.fill_between(time, -sbsb, -sbeb,
                        color='black', label='LOSS', alpha=0.3)

        ax.fill_between(time, -sbeb, -sbeb - smeoff,
                        color='b', alpha=0.3)
        
    else:
        ax.fill_between(time, 0, -smeoff,
                        color='b', alpha=0.3)
        
    title = f'# Energy #\n'
    if sbeion is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'Sun>{sbei[-1]:.2f}kWh'
        else:
            title += f'Sun>{sbei.sum():.2f}kWh'

    if sbeo is not None:
        title += '' if title[-1] == '\n' else ' | '
        if time_format == '%H:%M': # Accumulated
            title += f'Bank>{sbeo[-1]:.2f}kWh'
        else:
            title += f'Bank>{sbeo.sum():.2f}kWh~{sbeo.sum()*price:.2f}€'

    title += '' if title[-1] == '\n' else ' * '
    if sbebcharge is not None and (sbebcharge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'{sbebcharge[sbebcharge>0][-1]:.2f}kWh>'
        else:
            title += f'{sbebcharge[sbebcharge>0].sum():.2f}kWh>'

    title += 'BAT'
    
    if sbebdischarge is not None and (sbebdischarge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'>{sbebdischarge[sbebdischarge>0][-1]:.2f}kWh'
        else:
            title += f'>{sbebdischarge[sbebdischarge>0].sum():.2f}kWh'

    if sbsb is not None:
        title += f' #{sbsb[-1]:.2f}kWh~{sbsb[-1]/full_kwh*100:.0f}%'
            
            
    title += '' if title[-1] == '\n' else '\n'
        
    if iveon is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'Inv>{ive[-1]:.2f}kWh~{ive[-1]*price:.2f}€'
        else:
            title += f'Inv>{ive.sum():.2f}kWh~{ive.sum()*price:.2f}€'

    if spehon is not None:
        title += '' if title[-1] == '\n' else '\n'
        if time_format == '%H:%M': # Accumulated
            title += f'Plug0>{speh[-1]:.2f}kWh~{speh[-1]*price:.2f}€'
        else:
            title += f'Plug0>{speh.sum():.2f}kWh~{speh.sum()*price:.2f}€'

            
    title += '' if title[-1] == '\n' else ' | '            
            
    if smeoff is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'{smeoff[-1]:.2f}kWh~{(smeoff[-1]*price):.2f}€>'
        else:
            title += f'{smeoff.sum():.2f}kWh~{(smeoff.sum()*price):.2f}€>'

    title += f'Grid'
    
    if smeon is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'>{smeon[-1]:.2f}kWh~{(smeon[-1]*price):.2f}€'
        else:
            title += f'>{smeon.sum():.2f}kWh~{(smeon.sum()*price):.2f}€'

    if smeon is not None and smeoff is not None:            
        if time_format == '%H:%M': # Accumulated
            title += f' # Profit {(ive[-1]-smeoff[-1]):.2f}kWh~{(ive[-1]-smeoff[-1])*price:.2f}€'
        else:
            title += f' # Profit {ive.sum()-smeoff.sum():.2f}kWh~{(ive.sum()-smeoff.sum())*price:.2f}€'


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

async def get_kwh_line(
        time: t64s, smeon: f64s, smeoff: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh: f64s, full_kwh: f64s, price: f64,
        tphases: t64s = None,
        time_format: str = '%H:%M'):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(_get_kwh_line, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_kwh_line(**vars())


def _get_kwh_bar_unified(
        time: t64s, smeon: f64s, smeoff: f64s, balcony: f64s,
        price: f64, bar_width: f64, time_format: str):

    __me__='_get_kwh_bar_unified'
    logger.info(f'{__me__}: started')

    balconyon = balcony[balcony>0] if balcony is not None else None

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE+1))

    ax.clear()

    if balconyon is not None:
        logger.info(f'{__me__}: using unified samples')

        ax.bar(time, balcony, bottom = smeoff,
               color='cyan', label='BALCONY', width=bar_width, alpha=0.3)
        ax.bar(time, smeon, bottom=balcony+smeoff,
               color='blue',label='GRID >', width=bar_width, alpha=0.3)

        for x, ysmeoff, ybalcony, ysmeon in zip(time, smeoff, balcony, smeon):
            if ybalcony > 0.5 and ysmeoff < 0.0:
                ax.text(x, ysmeoff, f'{ybalcony:.1f}', ha = 'center',
                        color = 'grey', weight='bold', size=8)

            if ysmeoff + ybalcony > 0.5:
                ax.text(x, (ysmeoff + ybalcony)/2, f'{ysmeoff+ybalcony:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysmeon > 1.0:
                ax.text(x, ysmeoff + ybalcony + ysmeon/2 , f'{ysmeon:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)

    else:
        logger.info(f'{__me__}: using smartmeter samples only')

        if smeon is not None:
            ax.bar(time, smeoff, bottom = 0,
                   color='blue', width=bar_width, alpha=0.3)
        if smeoff is not None:
            ax.bar(time, smeon, bottom=balcony,
                   color='blue',label='GRID', width=bar_width, alpha=0.3)
            
                
    title = '' # f'# Energy Check #\n'
    if balconyon.any():
        title += f'Balcony {balconyon.sum():.1f}'
        title += f'={balconyon.mean():.1f}'
        title += f'^{balconyon.max():.1f}kWh'
        title += f'~{balconyon.sum()*price:.2f}€'

    smeonon = smeon[smeon>0]
    if smeonon.any():
        smeoffon = abs(smeoff)[abs(smeoff)>0]
        if smeoffon.any():
            title += f'\nProfit {(balconyon.sum()-smeoffon.sum()):.1f}kWh'
            title += f'~{((balconyon.sum()-smeoffon.sum())*price):.2f}€'
            title += f' ({(balconyon.sum()-smeoffon.sum())/balconyon.sum()*100:.0f}%)'
                
            title += f' | Gift {smeoffon.sum():.1f}kWh'
            title += f'~{smeoffon.sum()*price:.2f}€'
            title += f' ({smeoffon.sum()/balconyon.sum()*100:.0f}%)'

            title += f'\n{smeoffon.sum():.1f}'
            title += f'={smeoffon.mean():.1f}'
            title += f'^{smeoffon.max():.1f}kWh'   
            title += f'~{(smeoffon.sum()*price):.2f}€>'

            title += f'Grid'
            
            title += f'>{smeonon.sum():.1f}'
            title += f'={smeonon.mean():.1f}'
            title += f'^{smeonon.max():.1f}kWh'   
            title += f'~{(smeonon.sum()*price):.2f}€'

    ax.set_title(title, fontsize='x-large')

    ax.legend(loc="upper right")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='y')
    ax.grid(which='major', ls=':', lw=1, axis='x')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'{__me__}: done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')

async def get_kwh_bar_unified(
        time: t64s, smeon: f64s, smeoff: f64s, balcony: f64s,
        price: f64, bar_width: f64, time_format:str):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_kwh_bar_unified, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_kwh_bar_unified(**vars())


def _get_blocks(time: t64, smp: f64,
                ivp1: f64, ivp2: f64, spph: f64,
                sbpi: f64, sbpo: f64, sbpb: f64,
                spp1: f64, spp2: f64, spp3: f64, spp4: f64):
    __me__ ='_blocks'
    logger.info(f'{__me__}: started')

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.axis('equal')
    ax.axis('off')

    # Kann be anything! Only for relations
    BW, BH = 2, 2
    
    def _add_link_to_ax(ax: Any,
                        xb0: int, yb0: int, gate0: str,
                        xb1: int, yb1: int, gate1: str,
                        power: float, color: str, show_power: bool = True) -> None:

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

        lwidth = (2*np.log10(abs(power))+1) if abs(power)>0 else 0
        ax.plot(x, y, color=color, lw=lwidth, alpha=0.3)

        if show_power:
            ha, va = 'center', 'center' #if gate0 in "SN" and gate1 in "SN" else 'bottom'
            ltext = f'{power:.0f}W' if abs(power)>0 else ''
            ax.annotate(ltext, ((x[1]+x[3])/2, (y[2]+y[3])/2), color='black',
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
    grid = (4, 1)
    sinks = (4, -1)
    plug1 = (5.25 ,1)
    plug2 = (5.5 ,0.33)
    plug3 = (5.5 ,-0.33)
    plug4 = (5.25 ,-1)
        
    _add_box_to_ax(ax, *panel_1, 'PANEL1', 'green')
    _add_box_to_ax(ax, *panel_2, 'PANEL2', 'green')
    _add_box_to_ax(ax, *solix_mppt, 'MPPT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_split, 'SPLIT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_out, 'OUT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_bat, 'BAT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *house, 'METER\nHOUSE',
                   'blue' if smp>0 else 'magenta' if sbpb>0 else 'white')
    _add_box_to_ax(ax, *grid, 'POWER\nGRID',
                   'blue' if smp>0 else 'white')
    _add_box_to_ax(ax, *inv_mppt_1, 'MPPT1\nINV', 'cyan')
    _add_box_to_ax(ax, *inv_mppt_2, 'MPPT2\nINV', 'cyan')
    if spph>1:
        _add_box_to_ax(ax, *plugh, 'PLUG0\nBALCONY', 'brown')
    else:
        _add_box_to_ax(ax, *inv_out, 'OUT\nINV', 'cyan')
    _add_box_to_ax(ax, *sinks, 'MANY\nSINK', 'white')
    _add_box_to_ax(ax, *plug1, 'PLUG1\nSINK', 'white')
    _add_box_to_ax(ax, *plug2, 'PLUG2\nSINK', 'white')
    _add_box_to_ax(ax, *plug3, 'PLUG3\nSINK', 'white')
    _add_box_to_ax(ax, *plug4, 'PLUG4\nSINK', 'white')
    

    if sbpi>0 :
        _add_link_to_ax(
            ax, *panel_1, 'S', *solix_mppt, 'N',
            sbpi/2, 'green', show_power = False) # Measured only
        _add_link_to_ax(
            ax, *panel_2, 'N', *solix_mppt, 'S',
            sbpi/2, 'green', show_power = False) # Measured only
        _add_link_to_ax(
            ax, *solix_mppt, 'E', *solix_split, 'W',
            sbpi, 'grey')

    if sbpb<0 : #Charging
        _add_link_to_ax(
            ax, *solix_split, 'N', *solix_bat, 'W', sbpb, 'm')
    
    if sbpb>0 : #Discharging
        _add_link_to_ax(ax, *solix_bat, 'E', *solix_out, 'N',
                        sbpb, 'm',
                        show_power = sbpi+sbpb>ivp1+ivp2)

    if sbpi>0:
        _add_link_to_ax(ax, *solix_split, 'S', *solix_out, 'S',
                        sbpi+sbpb, 'grey',
                        show_power = sbpi+sbpb>ivp1+ivp2)

    
    if (sbpo>0) and (ivp1>0):
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_1, 'W',
                        ivp1 if ivp1>0 else sbpo/2,
                        'c' if ivp1>0 else 'grey',
                        show_power = ivp1>0)
    elif (ivp1>0) and not ((sbpb <0) or (sbpb >0)):
        _add_link_to_ax(ax, *panel_1, 'N', *inv_mppt_1, 'N',
                        ivp1, 'c',
                        show_power = ivp1>0)
        
    _add_link_to_ax(ax, *inv_mppt_1, 'S', *plugh, 'N',
                    ivp1 if ivp1>0 else sbpo/2,
                    'c' if ivp1>0 else 'grey',
                    show_power = False)            

    if  (sbpo >0) and  (ivp2>0):
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_2, 'W',
                        ivp2 if ivp2>0 else sbpo/2,
                        'c' if ivp2>0 else 'grey',
                        show_power = ivp2>0)
    elif (ivp2>0) and not ((sbpb <0) or (sbpb >0)):
        _add_link_to_ax(ax, *panel_2, 'S', *inv_mppt_2, 'S',
                        ivp2, 'c',
                        show_power = ivp2>0)

    _add_link_to_ax(ax, *inv_mppt_2, 'N', *plugh, 'S',
                    ivp2 if ivp2>0 else sbpo/2,
                    'c' if ivp2>0 else 'grey',
                    show_power = False)

    
    ivp = (ivp1+ivp2)

    balconyp = spph if spph>1 else ivp if ivp > 0 else sbpo
    
    if balconyp > 0:
        _add_link_to_ax(ax, *plugh, 'E', *house, 'W',
                        balconyp, 'c' if ivp>0 else 'grey')

    _add_link_to_ax(ax, *grid, 'S', *house, 'N', smp,
                    'blue' if smp>0 else 'brown')

    sinksp = smp + balconyp-spp1-spp2-spp3-spp4
    if sinksp > 1:
        _add_link_to_ax(ax, *house, 'S', *sinks, 'N', -sinksp, 'brown')

    if spp1>1:
        _add_link_to_ax(ax, *house, 'E', *plug1, 'W', -spp1, 'brown')
    if spp2>1:
        _add_link_to_ax(ax, *house, 'E', *plug2, 'W', -spp2, 'brown')
    if spp3>1:
        _add_link_to_ax(ax, *house, 'E', *plug3, 'W', -spp3, 'brown')
    if spp4>1:
        _add_link_to_ax(ax, *house, 'E', *plug4, 'W', -spp4, 'brown')


    # last sample time (python version independent)
    dt = datetime.strptime(str(time), '%Y-%m-%dT%H:%M:%S.%f000')
    hm = dt.strftime('%H:%M') 

    title = f'# System #'
    title += f'\nLast Sample of the Day @ {hm}'
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
                     spp1: f64, spp2: f64, spp3: f64, spp4: f64):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_blocks,**vars()) # type: ignore[unused-ignore]
    else:
        return _get_blocks(**vars())
