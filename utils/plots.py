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
logger = logging.getLogger(__file__)

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

    issmpon = smp>0 # Have data (smartmeter)
    smpon = smp[issmpon] if issmpon.any() else None
    smp_mean = smpon.mean() if smpon is not None else 0
    smp_max = smpon.max() if smpon is not None else 0
    
    ivp = ivp1 + ivp2
    isivpon = ivp>0 # Have data (inverter)
    ivpon = ivp[isivpon] if isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    issppon = spp>0 # Have data (smartplug)
    sppon = spp[issppon] if issppon.any() else None
    sppon_mean = sppon.mean() if sppon is not None else 0
    sppon_max = sppon.max() if sppon is not None else 0

    issbpion = sbpi>0 # Have sun (solarbank)
    sbpion = sbpi[issbpion] if issbpion.any() else None
    sbpion_mean = sbpion.mean() if sbpion is not None else 0
    sbpion_max = sbpion.max() if sbpion is not None else 0

    issbpoon = sbpo>0 # Have output (solarbank)
    sbpoon = sbpo[issbpoon] if issbpoon.any() else None
    sbpoon_mean = sbpoon.mean() if sbpoon is not None else 0
    sbpoon_max = sbpoon.max() if sbpoon is not None else 0
    
    issbpbon = sbpb<0 # Charging (solarbank)
    sbpbon = sbpb[issbpbon] if issbpbon.any() else None
    sbpbon_mean = sbpbon.mean() if sbpbon is not None else 0
    sbpbon_min = sbpbon.min() if sbpbon is not None else 0

    issbpboff = sbpb>0 # Discharging (solarbank)
    sbpboff = sbpb[issbpboff] if issbpboff.any() else None
    sbpboff_mean = sbpboff.mean() if sbpboff is not None else 0
    sbpboff_max = sbpboff.max() if sbpboff is not None else 0
    
    timeivpon = time[isivpon] if isivpon.any() else None
    timesppon = time[issppon] if issppon.any() else None
    timesbpbon = time[issbpbon] if issbpbon.any() else None
    timesbpboff = time[issbpboff] if issbpboff.any() else None
    timesbpoon = time[issbpoon] if issbpoon.any() else None
    timeon = timesppon if timesppon is not None else timeivpon 
    on600 = np.full_like(sppon if issppon.any() else ivpon, 600) 
    on800 = np.full_like(sppon if issppon.any() else ivpon, 800)

    totals = smp.copy()
    if sppon is not None: 
        totals += spp    # 1.priority (smartplug)
    elif ivpon is not None:
        totals += ivp    # 2.priority (inverter)
    elif sbpoon is not None:
        totals += sbpo   # 3.priority (solarbank)        
    slot_means = _power_means(time, totals, slots)

    logger.info('Plotting the power line image "w" started')

    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()
    
    if sppon is not None:
        """ The inverter is connected via a smartplug """
        
        ax.fill_between(time, 0, spp,
                        color='yellow',label='PLUG', lw=0, alpha=0.7)
        ax.fill_between(time, spp, spp  + smp,
                        color='b', label='HOUSE', lw=0, alpha=0.2)

        if ivpon is not None:
            ax.plot(time, ivp1,
                    color='c', lw=2, label='INVERTER 1', alpha=0.6)
            ax.plot(time, ivp1 + ivp2,
                    color='g', lw=2, label='INVERTER 2', alpha=0.6)

    elif ivpon is not None:
        """ The inverter is directly connected to the house and ok"""

        ax.fill_between(time, 0, ivp1,
                        color='c',label='INVERTER 1', alpha=0.6)
        ax.fill_between(time, ivp1, ivp1 + ivp2,
                        color='g', label='INVERTER 2', alpha=0.5)
        ax.fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smp,
                        color='b', label='HOUSE', alpha=0.2)

    elif sbpoon is not None:
        """ The solarbank output is used directly in spite of inverter """

        ax.fill_between(time, 0, sbpo,
                        color='orange',label='BANK', lw=0, alpha=0.7)
        ax.fill_between(time, sbpo, sbpo + smp,
                        color='b', label='HOUSE', lw=0, alpha=0.2)
        

    """ Plot the battery power of the solarbank """
    if sbpb is not None:
        ax.fill_between(time, 0, sbpb,
                        color='m', label='BAT', lw=0, alpha=0.2)

    """
    if sbpi is not None:
        ax.fill_between(time[issbpbon], sbpb[issbpbon], -sbpi[issbpbon],
                        color='c', label='SUN', alpha=0.2)
    """

    """
    if sbpoon is not None:
        ax.plot(time, sbpo,
                color='black', lw=2, label="BANK", alpha=0.2)
    """

    ax.plot(time, slot_means, 
            color='m', lw=2, label="MEAN", alpha=0.2)

    if timeon is not None:
        ax.fill_between(timeon , on600, on800,
                        color='orange', label='LIMITS', alpha=0.3)

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

    logger.info('Plotting the power line image "w" done')
    
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
    
    issmeon = sme>0
    smeon = sme[issmeon] if issmeon.any() else None

    ive = ive1 + ive2
    isiveon = ive>0
    iveon = ive[isiveon] if isiveon.any() else None

    isspeon = spe>0
    speon = spe[isspeon] if isspeon.any() else None

    issbeoon = sbeo>0
    sbeoon = sbeo[issbeoon] if issbeoon.any() else None
    
    logger.info('Plotting the energy line image "kwh" started ')

    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if speon is not None:
        ax.fill_between(time, 0, spe,
                             color='yellow', label='PLUG',alpha=0.6)
        ax.fill_between(time, spe, spe + sme,
                             color='b',label='HOUSE', alpha=0.2)

    elif iveon is not None:
        ax.fill_between(time, 0, ive1,
                             color='c', label='INVERTER 1',alpha=0.6)
        ax.fill_between(time, ive1, ive2 + ive1,
                             color='g',label='INVERTER 2', alpha=0.5)
        ax.fill_between(time, ive2 + ive1, ive2 + ive1 + sme,
                             color='b',label='HOUSE', alpha=0.2)

    elif sbeoon is not None:
        ax.fill_between(time, 0, sbeo,
                             color='orange', label='BANK',alpha=0.6)
        ax.fill_between(time, sbeo, sbeo + sme,
                             color='b',label='HOUSE', alpha=0.2)
        
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

    logger.info('Plotting the energy line image "kwh" done')

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


def _get_kwh_bar(time: t64s, sme: f64s,
                 ive1: f64s, ive2: f64s, spe: f64s,
                 price: f64, bar_width: f64, time_format: str):
    
    issmeon = sme>0
    smeon = sme[issmeon] if issmeon.any() else None

    ive = ive1 + ive2
    isiveon = ive>0
    iveon = ive[isiveon] if isiveon.any() else None

    isspeon = spe>0
    speon = spe[isspeon] if isspeon.any() else None

    #issbeoon = sbeo>0
    #sbeoon = sbeo[issbeoon] if issbeoon.any() else None
    sbeoon = None
    
    logger.info('Plotting the energy line image "kwh" started ')

    plt.switch_backend('Agg')
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if speon is not None:
        ax.bar(time, spe, bottom = 0,
               color='yellow', label='PLUG', width=bar_width, alpha=0.6)
        ax.bar(time, sme, bottom=spe,
               color='blue',label='HOUSE', width=bar_width, alpha=0.2)
        
        for x, yspe, ysme, ytot in zip(time, spe, sme, spe + sme):
            if yspe > 1.0:
                ax.text(x, yspe/2, f'{yspe:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysme > 1.0:
                ax.text(x, ysme/2 + yspe, f'{ysme:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            
    elif iveon is not None:
        ax.bar(time, ive1, bottom = 0,
               color='c', label='INVERTER 1', width=bar_width, alpha=0.6)
        ax.bar(time, ive2, bottom = ive1,
               color='g',label='INVERTER 2', width=bar_width, alpha=0.5)
        ax.bar(time, sme, bottom = ive,
               color='b',label='HOUSE', width=bar_width, alpha=0.2)

        for x, yspe, ysme, ytot in zip(time, ive1, ive2, sme):
            if yive1 > 1.0:
                ax.text(x, yive1/2, f'{yive1:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if yive2 > 1.0:
                ax.text(x, yive2/2 + yive1, f'{yive2:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysme > 1.0:
                ax.text(x, ysme/2 + yive2 + yive1, f'{ysme:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)

    elif sbeoon is not None:
        ax.bar(time, sbeo, bottom = 0,
               color='orange', label='BANK', width=bar_width, alpha=0.6)
        ax.bar(time, sme, bottom=sbeo,
               color='blue',label='HOUSE', width=bar_width, alpha=0.2)
        
        for x, ysbeo, ysme, ytot in zip(time, sbeo, sme, sbeo + sme):
            if ysbeo > 1.0:
                ax.text(x, ysbeo/2, f'{ysbeo:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysme > 1.0:
                ax.text(x, ysme/2 + ysbeo, f'{ysme:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
                
    title = f'Energy Check #'
    if smeon is not None:
        title += f' House {sme.sum():.1f}kWh ~ {(sme.sum()*price):.2f}€'
            
    if speon is not None:
        title += f' | Plug {spe.sum():.1f}kWh ~ {spe.sum()*price:.2f}€'
    elif iveon is not None:
        title += f' | Inv {ive.sum():.1f}kWh ~ {ive.sum()*price:.2f}€'
    elif sbeoon is not None:
        title += f' | Plug {sbeo.sum():.1f}kWh ~ {sbeo.sum()*price:.2f}€'
    ax.set_title(title, fontsize='x-large')

    ax.legend(loc="upper right")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='y')
    ##ax.grid(which='minor', ls='--', lw=1, axis='x')
    ##ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info('Plotting the energy line image "kwh" done')

    return base64.b64encode(buf.getbuffer()).decode('ascii')

async def get_kwh_bar(time: t64s, sme: f64s,
                      ive1: f64s, ive2: f64s, spe: f64s,
                      price: f64, bar_width: f64, time_format:str):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_kwh_bar, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_kwh_bar(**vars())
