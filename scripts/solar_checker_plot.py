#!/usr/bin/env python3

import sys
import argparse

import pandas as pd
import numpy as np

import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime, timedelta

def str2date(value):
    return datetime.fromisoformat(value)

def str2float(value):
    return float(value)


def plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2):
        dformatter = mdates.DateFormatter('%H:%M')
        #dformatter.set_tzinfo(self.tzinfo)

        fig, axes = plt.subplots(nrows=2, figsize=(12,6))

        text = f'Solar Checker'
        fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')
        
        axes[0].fill_between(time, smp+ivp1+ivp2, color='green', linewidth=2,label='APSYSTEMS 1+2', alpha=0.5)
        axes[0].fill_between(time, smp+ivp1, color='cyan', linewidth=2,alpha=0.7)
        axes[0].fill_between(time, smp, color='blue', label='TASMOTA', alpha=0.5)
        axes[0].legend(loc="upper left")
        axes[0].grid(which='major', linestyle='-', linewidth=2, axis='both')
        axes[0].grid(which='minor', linestyle='--', linewidth=1, axis='x')
        axes[0].minorticks_on()
        title = f'Power Check #'
        title += f' Tasmota max:{np.max(smp):.0f}W | APsystems max:{np.max((ivp1+ivp2)[(ivp1+ivp2)>0]):.0f}'
        axes[0].set_title(title, fontsize='x-large')
        axes[0].set_ylabel('Watts [W]')
        axes[0].xaxis.set_major_formatter(dformatter)

        sm = sme-sme[0]
        iv = ive1-ive1[0] + ive2-ive2[0]
        axes[1].plot(time, iv, color='green', linewidth=2,label='APSYSTEMS 1+2', alpha=0.5)
        axes[1].plot(time, sm, color='blue', linewidth=3,label='TASMOTA', alpha=0.9)
        axes[1].legend(loc="upper left")
        axes[1].grid(which='major', linestyle='-', linewidth=2, axis='both')
        axes[1].grid(which='minor', linestyle='--', linewidth=1, axis='x')
        axes[1].minorticks_on()
        title = f'Energy Check #'
        title += f' Tasmota {sm[-1]:.1f}kWh | APsystems {iv[iv>0][-1]:.3f}kWh'
        axes[1].set_title(title, fontsize='x-large')
        axes[1].set_ylabel('Work [Wh]')
        axes[1].xaxis.set_major_formatter(dformatter)
        
        fig.tight_layout(pad=2.0)

        ##fig.savefig(name)
        ##plt.close(fig) 
        plt.show()

        
def check_powers(f = sys.stdin):
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2'.split(',')
    df = pd.read_csv(f, sep = sep, names = names)

    """ The timestamps """
    time = np.array(df.TIME.apply(str2date))
    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(str2float))    
    """ The inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(str2float))
    """ The inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(str2float))

    """ The smartmeter energy samples """
    sme = np.array(df.SME.apply(str2float))    
    """ The inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(str2float))
    """ The inverter power samples channel 2 """
    ive2 = np.array(df.IVE2.apply(str2float))
    
    plot_powers(time, smp, ivp1, ivp2, sme, ive1, ive2)

    return 0


def parse_args():
    parser = argparse.ArgumentParser(description='Plot MPPT Volts')

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    check_powers()
    return 0

if __name__ == '__main__':
    sys.exit(main())
