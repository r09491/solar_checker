#!/usr/bin/env python3

__doc__="""
Checks the solar power input of micro inverters against the
consumption measured by smartmeter in a houshold

Plots the power output in logarithmic scale to emphasise lower values
and the energy in linear scale.

Plots the power output means for defined time slots to help in
scheduling of battery outputs if they can.
"""
__version__ = "0.0.2"
__author__ = "r09491@t-online.de"

import os
import sys
import argparse

import pandas as pd
import numpy as np

import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime, timedelta

#import warnings
#warnings.simplefilter("ignore")


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


def iso2date(value):
    dt = datetime.fromisoformat(value)
    return np.datetime64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

def hm2date(value):
    dt = datetime.strptime(value,"%H:%M")
    return np.datetime64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

def str2float(value):
    return float(value)


SLOTS = ["00:00", "07:00", "10:00", "14:00", "17:00", "22:00", "23:59"]
def power_means(times, powers, slots = SLOTS):
    spowers = np.full_like(powers, 0.0)
    for start, stop in zip(slots[:-1], slots[1:]):
        wheres, = np.where((times >= hm2date(start)) & (times <= hm2date(stop)))
        spowers[wheres] = powers[wheres].mean() if wheres.size > 0 else None
    return spowers


def plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2, spp, price):

    smp_mean = smp.mean()
    smp_max = smp.max()
    
    ivp = ivp1 + ivp2

    isivpon = ivp>0
    ivpon = ivp[isivpon] if isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    timeivpon = time[isivpon] if isivpon.any() else None
    ivpon600 = np.full_like(ivpon, 600) 
    ivpon800 = np.full_like(ivpon, 800)

    total_means = power_means( time, smp + ivp)

    dformatter = mdates.DateFormatter('%H:%M')

    fig, axes = plt.subplots(nrows=2, figsize=(12,8))

    text = f'Solar Checker'
    fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')

    axes[0].fill_between(time, 0, ivp1,
                         color='c',label='APSYSTEMS 1', alpha=0.6)
    axes[0].fill_between(time, ivp1, ivp1 + ivp2,
                         color='g', label='APSYSTEMS 2', alpha=0.5)
    axes[0].fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smp,
                         color='b', label='TASMOTA', alpha=0.2)

    if spp is not None:
        axes[0].plot(time, spp,
                     color='yellow', lw=2, label="PLUG")
    
    axes[0].plot(time, total_means,
                 color='m', lw=2, label="TOTAL MEAN")

    if timeivpon is not None:
        axes[0].fill_between(timeivpon, ivpon600, ivpon800,
                    color='orange', label='LIMITS', alpha=0.6)

    title = f'Power Check #'
    if smp.size > 0 and smp[-1] >= 0:
        title += f' Tasmota {smp[-1]:.0f}'
        title += f'={smp_mean:.0f}^{smp_max:.0f}W'
        
    if ivp.size > 0 and ivp[-1] >= 0:
        title += f' | APsystems {ivp[-1]:.0f}'
    if ivpon is not None:
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'
    axes[0].set_title(title, fontsize='x-large')        

    axes[0].legend(loc="upper left")
    axes[0].set_ylabel('Power [W]')
    axes[0].set_yscale("log")
    axes[0].xaxis_date()
    axes[0].xaxis.set_major_formatter(dformatter)
    axes[0].grid(which='major', ls='-', lw=2, axis='both')
    axes[0].grid(which='minor', ls='--', lw=1, axis='both')
    axes[0].minorticks_on()
    

    ive = ive1 + ive2

    axes[1].fill_between(time, 0, ive1,
                         color='c', label='APSYSTEMS 1',alpha=0.6)
    axes[1].fill_between(time, ive1, ive2 + ive1,
                         color='g',label='APSYSTEMS 2', alpha=0.5)
    axes[1].fill_between(time, ive2 + ive1, ive2 + ive1 + sme,
                         color='b',label='TASMOTA', alpha=0.2)

    title = f'Energy Check #'
    if sme.size > 0 and sme[-1] >= 0:
        title += f' Tasmota {sme[-1]:.1f}kWh ~ {(sme[-1]*price):.2f}€'
    if ive.size > 0 and ive[-1] >= 0:
        title += f' | APsystems {ive[-1]:.3f}kWh ~ {ive[-1]*price:.2f}€'
    axes[1].set_title(title, fontsize='x-large')

    axes[1].legend(loc="upper left")
    axes[1].set_ylabel('Energy [Wh]')
    axes[1].xaxis_date()
    axes[1].xaxis.set_major_formatter(dformatter)
    axes[1].grid(which='major', ls='-', lw=2, axis='both')
    axes[1].grid(which='minor', ls='--', lw=1, axis='x')
    axes[1].minorticks_on()

    fig.tight_layout(pad=2.0)

    ##fig.savefig(name)
    ##plt.close(fig) 
    plt.show()

        
def check_powers(price, f = sys.stdin):
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPP'.split(',')
    df = pd.read_csv(f, sep = sep, names = names)

    """
    The data contain invalid data (nan) due to errors during
    recording.  The 'nan' are replaced by some plausile values: 0.0
    for the power, the last valid recording for the energy.
    """

    """ The timestamps """
    time = np.array(df.TIME.apply(iso2date))

    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(str2float))
    if np.isnan(smp).any():
        logger.error(f'Undefined SMP samples')
        return 2
    
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(str2float))
    if np.isnan(ivp1).any():
        logger.error(f'Undefined IVP1 samples')
        return 2

    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(str2float))
    if np.isnan(ivp2).any():
        logger.error(f'Undefined IVP2 samples')
        return 3

    """ The normalised smartmeter energy samples """
    sme = np.array(df.SME.apply(str2float))
    if np.isnan(sme).any():
        logger.error(f'Undefined SME samples')
        return 4
    
    """ The normalised inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(str2float))
    if np.isnan(ive1).any():
        logger.error(f'Undefined IVE2 samples')
        return 5
    
    """ The normalised inverter energy samples channel 2 """
    ive2 = np.array(df.IVE2.apply(str2float))
    if np.isnan(ive2).any():
        logger.error(f'Undefined IVE2 samples')
        return 6

    """ The normalised smartplug power """
    spp = np.array(df.SPP.apply(str2float))
    if np.isnan(spp).any():
        logger.warning(f'Undefined SPP samples')
        spp = None
    
    # Get rid of offsets and fill tails

    sme -= sme[0]
    sme[sme<0.0] = 0.0
    sme[np.argmax(sme)+1:] = sme[np.argmax(sme)]

    ive1[ive1<0.0] = 0.0
    ive1 -= ive1[0]
    ive1[np.argmax(ive1)+1:] = ive1[np.argmax(ive1)]

    ive2 -= ive2[0]
    ive2[ive2<0.0] = 0.0
    ive2[np.argmax(ive2)+1:] = ive2[np.argmax(ive2)]

    """ ! All arrays are expected to have the same length ! """

    plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2, spp, price)

    return 0


def parse_args():
    parser = argparse.ArgumentParser(description='Check solar power input against power consumption in a house')

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--price', type = float, default = 0.369,
                        help = "The price of energy per kWh")

    return parser.parse_args()


def main():
    args = parse_args()

    err = 0
    
    try:
        err = check_powers(args.price)
    except KeyboardInterrupt:
        pass
    except TypeError:
        """If there is no stream"""
        pass
    
    return err

if __name__ == '__main__':
    sys.exit(main())
