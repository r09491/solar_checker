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

import numpy as np
import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format

#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
#import matplotlib.dates as mdates

import asyncio

from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.typing import t64, t64s, timeslots, Any, List
from utils.samples import get_columns_from_csv


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

        
async def show_slots(
        slots: List[str],
        times: List[str]
) -> int:
    _log = await get_columns_from_csv()
    if len(_log) == 0:
        logger.error("Missing log input!")
        return -1
    
    log = pd.DataFrame(_log).loc[:,["TIME", "SBPI", "SMP"]]
    log['TIME'] = pd.to_datetime(log['TIME'])
    log.set_index('TIME', inplace=True, drop=True)

    log = log.resample("min").nearest()
    if log.size != 2*24*60:
         logger.error(f'Log for complete day is required')
         return -2
       
    # The date the log was created
    date = log.index[0].date()
    starts, ends = times[:-1], times[1:]
    ranges = [
        pd.date_range(
            start=f"{date} {start}",
            end=f"{date} {end}",
            freq="min",
            inclusive="left"
        ) for start, end in zip(starts, ends)
    ]


    means = [log.loc[r,:].mean() for r in ranges]
    maxs = [log.loc[r,:].max() for r in ranges]
    stds = [log.loc[r,:].std() for r in ranges]


    sdf_means = pd.DataFrame(
        index = slots,
        data = means
    ).add_suffix("_mean")

    sdf_maxs = pd.DataFrame(
        index = slots,
        data = maxs
    ).add_suffix("_max")

    sdf_stds = pd.DataFrame(
        index = slots,
        data = stds
    ).add_suffix("_std")

    sdf = pd.concat([sdf_means,sdf_maxs, sdf_stds], axis=1)
    
    print(f'\nSlots for "{date}"')
    print(sdf)

    return 0


# def hm2time(hm: str) -> t64s:
#     return t64(datetime.strptime(hm, "%H:%M"))
def hm2time(hm: str) -> str:
    return hm


@dataclass
class Script_Arguments:
    midnight: str
    morning: str
    noon: str
    afternoon: str
    evening: str
    night: str
    daystop: str

def parse_args() -> Script_Arguments:
    description='Show some statistics for time slots'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)
    
    parser.add_argument(
        '--morning', type=hm2time, default = "07:30",
        help = "The start hour of the morning slot")

    parser.add_argument(
        '--noon', type=hm2time, default = "09:30",
        help = "The start hour of the noon slot")

    parser.add_argument(
        '--afternoon', type=hm2time, default = "14:00",
        help = "The start hour of the afternoon slot")

    parser.add_argument(
        '--evening', type=hm2time, default = "19:30",
        help = "The start hour of the evening slot")

    parser.add_argument(
        '--night', type=hm2time, default = "22:30",
        help = "The start hour of the midnight slot")

    args = parser.parse_args()
    
    return Script_Arguments(hm2time("00:00"),
                            args.morning,
                            args.noon,
                            args.afternoon,
                            args.evening,
                            args.night,
                            hm2time("23:59"))


async def main() -> int:
    args = parse_args()

    slots = [
        "MIDNIGHT",
        "MORNING",
        "NOON",
        "AFTERNOON",
        "EVENING",
        "NIGHT",
        "DAYSTOP"
    ]

    times = [
        hm2time("00:00"),
        args.morning,
        args.noon,
        args.afternoon,
        args.evening,
        args.night, 
        hm2time("23:59")
    ]

    try:
        await show_slots( slots[:-1], times)
    except KeyboardInterrupt:
        pass
    
    return 0

if __name__ == '__main__':
    try:
        err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
    sys.exit(err)
