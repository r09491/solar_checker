#!/usr/bin/env python3

__doc__="""
Checks the solar power input of micro APsystems inverters against the
consumption measured by a Tasmota smartmeter in a houshold. The
APsystems inverters are to be operated in direct local mode.

Checks the input of APsystems inverters to an Antella smartplug
against the consumption measured by a Tasmota smartmeter in a
houshold. The plug may be present or absent.  If present has priority
over APsystems measuremnents.

Plots the power output in logarithmic scale to emphasise lower values
and the energy in linear scale.

Plots the power output means for defined time slots to help in
scheduling of battery outputs if they can.
"""
__version__ = "0.0.3"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse

import pandas as pd
import numpy as np
from numpy.typing import NDArray # mypy Crash!"

import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime, timedelta

#import warnings
#warnings.simplefilter("ignore")

from typing import Any
from dataclasses import dataclass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


f64 = np.float64
f64s = NDArray[f64]

t64 = np.datetime64
t64s = NDArray[t64]

def iso2date(value: str) -> t64:
    dt = datetime.fromisoformat(value)
    return t64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

def hm2date(value: str) -> t64:
    dt = datetime.strptime(value,"%H:%M")
    return t64(datetime(year=1900, month=1, day=1, minute=dt.minute, hour=dt.hour))

def str2float(value: str) -> f64:
    return f64(value)


SLOTS = ["00:00", "07:00", "10:00", "14:00", "17:00", "22:00", "23:59"]
def power_means(times: t64s,
                powers: f64s, slots: list[str] = SLOTS) -> f64s:
    spowers = np.full_like(powers, 0.0)
    for start, stop in zip(slots[:-1], slots[1:]):
        wheres, = np.where((times >= hm2date(start)) & (times <= hm2date(stop)))
        spowers[wheres] = powers[wheres].mean() if wheres.size > 0 else None
    return spowers


def plot_powers(time: t64s,
                smp: f64s, ivp1: f64s, ivp2: f64s,
                sme: f64s, ive1: f64s, ive2: f64s,
                spp: f64s, price: f64) -> int:

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

    
    dformatter = mdates.DateFormatter('%H:%M') # type: ignore[no-untyped-call]
    fig, axes = plt.subplots(nrows=2, figsize=(12,8))

    text = f'Solar Checker'
    fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')

    if sppon is not None:
        axes[0].fill_between(time, 0, spp,
                             color='yellow',label='PLUG', alpha=0.6)
        axes[0].fill_between(time, spp, spp  + smp,
                             color='b', label='HOUSE', alpha=0.2)

        if ivpon is not None:
            axes[0].plot(time, ivp1,
                         color='c', lw=2, label='INVERTER 1', alpha=0.6)
            axes[0].plot(time, ivp1 + ivp2,
                     color='g', lw=2, label='INVERTER 2', alpha=0.6)

    else:
        axes[0].fill_between(time, 0, ivp1,
                             color='c',label='INVERTER 1', alpha=0.6)
        axes[0].fill_between(time, ivp1, ivp1 + ivp2,
                         color='g', label='INVERTER 2', alpha=0.5)
        axes[0].fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smp,
                             color='b', label='HOUSE', alpha=0.2)
    
    axes[0].plot(time, total_means, 
                 color='m', lw=2, label="TOTAL MEAN")

    if timeon is not None:
        axes[0].fill_between(timeon , on600, on800,
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
            
    axes[0].set_title(title, fontsize='x-large')        

    axes[0].legend(loc="upper left")
    axes[0].set_ylabel('Power [W]')
    axes[0].set_yscale("log")
    axes[0].xaxis_date()
    axes[0].xaxis.set_major_formatter(dformatter)
    axes[0].grid(which='major', ls='-', lw=2, axis='both')
    axes[0].grid(which='minor', ls='--', lw=1, axis='both')
    axes[0].minorticks_on()
    


    if sppon is not None:
        spe = spp.cumsum()/1000/60 # kWh
    
        axes[1].fill_between(time, 0, spe,
                             color='yellow', label='PLUG',alpha=0.6)
        axes[1].fill_between(time, spe, spe + sme,
                             color='b',label='HOUSE', alpha=0.2)
    else:
        ive = ive1 + ive2

        axes[1].fill_between(time, 0, ive1,
                             color='c', label='INVERTER 1',alpha=0.6)
        axes[1].fill_between(time, ive1, ive2 + ive1,
                             color='g',label='INVERTER 2', alpha=0.5)
        axes[1].fill_between(time, ive2 + ive1, ive2 + ive1 + sme,
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
    axes[1].set_title(title, fontsize='x-large')

    axes[1].legend(loc="upper left")
    axes[1].set_ylabel('Energy [Wh]')
    axes[1].xaxis_date()
    axes[1].xaxis.set_major_formatter(dformatter)
    axes[1].grid(which='major', ls='-', lw=2, axis='both')
    axes[1].grid(which='minor', ls='--', lw=1, axis='x')
    axes[1].minorticks_on()

    fig.tight_layout(pad=2.0) # type: ignore[no-untyped-call]

    ##fig.savefig(name)
    ##plt.close(fig) 
    plt.show()

    return 0

        
def check_powers(price: f64, f: Any = sys.stdin) -> int:
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
        logger.error(f'Undefined SPP samples')
        return 7
    
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


@dataclass
class Script_Arguments:
    price: f64

def parse_arguments() -> Script_Arguments:

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Check solar power input',
        epilog=__doc__)
        
    parser.add_argument('--version',
                        action = 'version', version = __version__)

    parser.add_argument('--price', type = f64, default = 0.369,
                        help = "The price of energy per kWh")

    args = parser.parse_args()
    return Script_Arguments(args.price)


def main() -> int:
    args = parse_arguments()

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
