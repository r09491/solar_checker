import os
import sys

import base64
from io import BytesIO

from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import numpy as np

from .types import f64, f64s, t64, t64s, timeslots

def hm2date(value: str) -> t64:
    dt = datetime.strptime(value,"%H:%M")
    return t64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

SLOTS = ["00:00", "07:00", "10:00", "14:00", "17:00", "22:00", "23:59"]
def power_means(times: t64s,
                powers: f64s, slots: timeslots = SLOTS) -> f64s:
    spowers = np.full_like(powers, 0.0)
    for start, stop in zip(slots[:-1], slots[1:]):
        wheres, = np.where((times >= hm2date(start)) & (times <= hm2date(stop)))
        spowers[wheres] = powers[wheres].mean() if wheres.size > 0 else None
    return spowers


XSIZE, YSIZE = 9, 3

def get_w_image(time: t64s, smp: f64s, ivp1: f64s, ivp2: f64s, spp: f64s):
    smp_mean = smp.mean()
    smp_max = smp.max()
    
    ivp = ivp1 + ivp2

    isivpon = ivp>0
    ivpon = ivp[isivpon] if isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    issppon = spp>0
    sppon = spp[issppon] if issppon.any() else None
    sppon_mean = sppon.mean() if sppon is not None else 0
    sppon_max = sppon.max() if sppon is not None else 0

    timeivpon = time[isivpon] if isivpon.any() else None
    timesppon = time[issppon] if issppon.any() else None
    timeon = timesppon if timesppon is not None else timeivpon 
    on600 = np.full_like(sppon if issppon.any() else ivpon, 600) 
    on800 = np.full_like(sppon if issppon.any() else ivpon, 800)
    
    total_means = power_means( time, smp + spp if issppon.any() else ivp)

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()
    

    if sppon is not None:
        ax.fill_between(time, 0, spp,
                             color='yellow',label='PLUG', alpha=0.6)
        ax.fill_between(time, spp, spp  + smp,
                             color='b', label='HOUSE', alpha=0.2)

        if ivpon is not None:
            ax.plot(time, ivp1,
                         color='c', lw=2, label='INVERTER 1', alpha=0.6)
            ax.plot(time, ivp1 + ivp2,
                     color='g', lw=2, label='INVERTER 2', alpha=0.6)

    else:
        ax.fill_between(time, 0, ivp1,
                             color='c',label='INVERTER 1', alpha=0.6)
        ax.fill_between(time, ivp1, ivp1 + ivp2,
                         color='g', label='INVERTER 2', alpha=0.5)
        ax.fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smp,
                             color='b', label='HOUSE', alpha=0.2)
    
    ax.plot(time, total_means, 
                 color='m', lw=2, label="TOTAL MEAN")

    if timeon is not None:
        ax.fill_between(timeon , on600, on800,
                    color='orange', label='LIMITS', alpha=0.6)

    title = f'Power Check #'
    if smp.size > 0 and smp[-1] >= 0:
        title += f' House {smp[-1]:.0f}'
        title += f'={smp_mean:.0f}^{smp_max:.0f}W'

    if sppon is not None:
        if spp.size > 0 and spp[-1] >= 0:
            title += f' | Plug {spp[-1]:.0f}'
        if sppon.size is not None:
            title += f'={sppon_mean:.0f}^{sppon_max:.0f}W'
    else:
        if ivp.size > 0 and ivp[-1] >= 0:
            title += f' | Inverter {ivp[-1]:.0f}'
        if ivpon is not None:
            title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'
            
    ax.set_title(title, fontsize='x-large')        

    ax.legend(loc='upper left')
    ax.set_ylabel('Power [W]')
    ax.set_yscale('log')
    ax.xaxis_date()
    hm_formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(hm_formatter)
    ax.grid(which='major', ls='-', lw=2, axis='both')
    ax.grid(which='minor', ls='--', lw=1, axis='both')
    ax.minorticks_on()
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    
    return base64.b64encode(buf.getbuffer()).decode('ascii')


def get_wh_image(time: t64s, sme: f64s, ive1: f64s, ive2: f64s, spp: f64s, price: f64):
    issppon = spp>0
    sppon = spp[issppon] if issppon.any() else None

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if sppon is not None:
        spe = spp.cumsum()/1000/60 # kWh
    
        ax.fill_between(time, 0, spe,
                             color='yellow', label='PLUG',alpha=0.6)
        ax.fill_between(time, spe, spe + sme,
                             color='b',label='HOUSE', alpha=0.2)
    else:
        ive = ive1 + ive2

        ax.fill_between(time, 0, ive1,
                             color='c', label='INVERTER 1',alpha=0.6)
        ax.fill_between(time, ive1, ive2 + ive1,
                             color='g',label='INVERTER 2', alpha=0.5)
        ax.fill_between(time, ive2 + ive1, ive2 + ive1 + sme,
                             color='b',label='HOUSE', alpha=0.2)

    title = f'Energy Check #'
    if sme.size > 0 and sme[-1] >= 0:
        title += f' House {sme[-1]:.1f}kWh ~ {(sme[-1]*price):.2f}€'

    if sppon is not None:
        if spe.size > 0 and spe[-1] >= 0:
            title += f' | Plug {spe[-1]:.3f}kWh ~ {spe[-1]*price:.2f}€'
    else:
        if ive.size > 0 and ive[-1] >= 0:
            title += f' | Inverter {ive[-1]:.3f}kWh ~ {ive[-1]*price:.2f}€'
    ax.set_title(title, fontsize='x-large')

    ax.legend(loc="upper left")
    ax.set_ylabel('Energy [Wh]')
    ax.xaxis_date()
    hm_formatter = mdates.DateFormatter('%H:%Mh')
    ax.xaxis.set_major_formatter(hm_formatter)
    ax.grid(which='major', ls='-', lw=2, axis='both')
    ax.grid(which='minor', ls='--', lw=1, axis='x')
    ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    return base64.b64encode(buf.getbuffer()).decode('ascii')
