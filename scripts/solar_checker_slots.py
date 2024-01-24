#!/usr/bin/env python3

__doc__="""
Shows statistical data for the morning, noon, afternoon, evening and
night slots. The start hours for the slots are 07:00, 10:00, 14:00,
17:00, 22:00 per default in that order. The stop hour is the start
hour of the next slot. The start hours can be modified on the command
line.

This may be used to plan time slots for my Anker Solix 1600.
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse

import pandas as pd
import numpy as np

#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
#import matplotlib.dates as mdates

from datetime import datetime, timedelta

from typing import Any
from dataclasses import dataclass

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


def iso2date(value: str) -> np.datetime64:
    dt = datetime.fromisoformat(value)
    return np.datetime64(datetime(year=1900, month=1, day=1,
                                  minute=dt.minute, hour=dt.hour))


def str2float(value:str) -> float:
    return float(value)


        
def show_slots(slots: list[str],
               starts: list[np.datetime64],
               stops: list[np.datetime64], f: Any = sys.stdin) -> int:
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
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(str2float))
    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(str2float))
    """ The normalised inverter power sum """
    ivp = ivp1 + ivp2

    """ The normalised smartplug power """
    spp = np.array(df.SPP.apply(str2float))
        
    for slot, start, stop in zip(slots, starts, stops):
        wheres, = np.where((time >= start) & (time < stop))
        if wheres.size == 0: continue
        
        smps, ivps, spps = smp[wheres], ivp[wheres], spp[wheres]

        text = f"'{slot}'"
        text += f" > smp={smps.mean():.0f}^{smps.max():.0f}W"
        text += f" | ivp={ivps.mean():.0f}^{ivps.max():.0f}W"
        text += f" | spp={spps.mean():.0f}^{spps.max():.0f}W"
        logger.info(text)

    return 0


def hm2time(hm: str) -> np.datetime64:
    return np.datetime64(datetime.strptime(hm, "%H:%M"))


@dataclass
class Script_Arguments:
    midnight: np.datetime64
    morning: np.datetime64
    noon: np.datetime64
    afternoon: np.datetime64
    evening: np.datetime64
    night: np.datetime64
    daystop: np.datetime64

def parse_args() -> Script_Arguments:
    description='Show some statistics for time slots'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)
    
    parser.add_argument(
        '--morning', type=hm2time, default = "07:00",
        help = "The start hour of the morning slot")

    parser.add_argument(
        '--noon', type=hm2time, default = "10:00",
        help = "The start hour of the noon slot")

    parser.add_argument(
        '--afternoon', type=hm2time, default = "14:00",
        help = "The start hour of the afternoon slot")

    parser.add_argument(
        '--evening', type=hm2time, default = "17:00",
        help = "The start hour of the evening slot")

    parser.add_argument(
        '--night', type=hm2time, default = "22:00",
        help = "The start hour of the midnight slot")

    args = parser.parse_args()
    
    return Script_Arguments(hm2time("00:00"),
                            args.morning, args.noon,
                            args.afternoon, args.evening,
                            args.night,hm2time("23:59"))


def main() -> int:
    args = parse_args()

    times = {
        "midnight" : hm2time("00:00"),
        "morning" : args.morning,
        "noon" : args.noon,
        "afternoon" : args.afternoon,
        "evening" : args.evening,
        "night" : args.night, 
        "daystop" : hm2time("23:59")
    }

    
    slots = list((times.keys()))
    starts = [t for _, t in list(times.items())[:-1]]
    stops = [t for _, t in list(times.items())[1:]]

    for slot, start, stop in zip(slots, starts, stops):
        text = f"'{slot}'"
        text += f" from '{start.astype(datetime).strftime('%H:%M')}'"
        text += f" to '{stop.astype(datetime).strftime('%H:%M')}'"
        logger.info(text)
        
    if (np.array(starts) > np.array(stops)).any():
        si = np.argmax(np.array(starts)>np.array(stops))
        logger.error(f"Wrong order of slot times '{slots[si]}' is '{starts[si].astype(datetime).strftime('%H:%M')}'")
        return 1
    
    try:
        show_slots(slots, starts, stops)
    except KeyboardInterrupt:
        pass
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
