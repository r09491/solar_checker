#!/usr/bin/env python3

__doc__="""
Checks the solar power input of micro inverters against the
consumption measured by smartmeter in a houshold
"""
__version__ = "0.0.1"
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

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


def str2date(value):
    return datetime.fromisoformat(value)

def str2float(value):
    return float(value)


def plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2, price):

    dformatter = mdates.DateFormatter('%H:%M')

    fig, axes = plt.subplots(nrows=2, figsize=(12,6))

    text = f'Solar Checker'
    fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')

    ivp = ivp1 + ivp2

    axes[0].fill_between(time, smp + ivp1 + ivp2, color='green', label='APSYSTEMS 1+2', alpha=0.5)
    axes[0].fill_between(time, smp + ivp1, color='cyan', alpha=0.5)
    axes[0].fill_between(time, smp, color='blue', label='TASMOTA', alpha=0.5)
    axes[0].axhline(np.mean(smp), color='magenta', linewidth=2, label="MEAN")
    axes[0].legend(loc="upper left")
    axes[0].grid(which='major', linestyle='-', linewidth=2, axis='both')
    axes[0].grid(which='minor', linestyle='--', linewidth=1, axis='x')
    axes[0].minorticks_on()
    title = f'Power Check #'
    if len(smp) > 0:
        title += f' Tasmota {smp[-1]:.0f}={np.mean(smp):.0f}^{np.max(smp):.0f}W'
    if len(ivp) > 0:
        title += f' | APsystems {ivp[-1]:.0f}={np.mean(ivp):.0f}^{np.max(ivp):.0f}W'
    axes[0].set_title(title, fontsize='x-large')
    axes[0].set_ylabel('Watts [W]')
    axes[0].xaxis.set_major_formatter(dformatter)

    
    ive = ive1 + ive2

    axes[1].fill_between(time, sme + ive1 + ive2,
                         color='green',label='APSYSTEMS 1+2', alpha=0.5)
    axes[1].fill_between(time, sme + ive1,
                         color='cyan', alpha=0.5)
    axes[1].fill_between(time, sme,
                         color='blue',label='TASMOTA', alpha=0.5)
    axes[1].legend(loc="upper left")
    axes[1].grid(which='major', linestyle='-', linewidth=2, axis='both')
    axes[1].grid(which='minor', linestyle='--', linewidth=1, axis='x')
    axes[1].minorticks_on()
    title = f'Energy Check #'
    if len(sme) > 0:
        title += f' Tasmota {sme[-1]:.1f}kWh > {(sme[-1]*price):.2f}€'
    if len(ive) > 0:
        title += f' | APsystems {ive[-1]:.3f}kWh > {ive[-1]*price:.2f}€'
    axes[1].set_title(title, fontsize='x-large')
    axes[1].set_ylabel('Work [Wh]')
    axes[1].xaxis.set_major_formatter(dformatter)
        
    fig.tight_layout(pad=2.0)

    ##fig.savefig(name)
    ##plt.close(fig) 
    plt.show()

        
def check_powers(price, f = sys.stdin):
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2'.split(',')
    df = pd.read_csv(f, sep = sep, names = names)
    
    """ The timestamps """
    time = np.array(df.TIME.apply(str2date))
    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(str2float))    
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(str2float))
    ivp1[np.isnan(ivp1)] = 0.0
    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(str2float))
    ivp2[np.isnan(ivp2)] = 0.0

    """ The normalised smartmeter energy samples """
    sme = np.array(df.SME.apply(str2float))
    sme[~np.isnan(sme)] 
    sme -= sme[0]
    """ The normalised inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(str2float))
    ive1[np.isnan(ive1)] = 0.0
    """ The normalised inverter energy samples channel 2 """
    ive2 = np.array(df.IVE2.apply(str2float))
    ive2[np.isnan(ive2)] = 0.0

    """ ! All arrays are expected to have the same length ! """
    
    plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2, price)

    return 0


def parse_args():
    parser = argparse.ArgumentParser(description='Check solar power input against power consumption in a house')

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--price', type = float, default = 0.369,
                        help = "The price of energy per kWh")

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        check_powers(args.price)
    except KeyboardInterrupt:
        pass
    except TypeError:
        """If there is no stream"""
        pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
