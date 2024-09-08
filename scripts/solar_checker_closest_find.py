#!/usr/bin/env python3

__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import pandas as pd
import numpy as np

from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.types import t64, t64s, timeslots, Any
from utils.common import sample_names
from utils.samples import get_columns_from_csv
from utils.samples import get_logdays


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

        
async def find_closest(
        logday: str,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        start_time: t64,
        stop_time: t64,
        column: t64) -> int:

    # Get the columns of the reference day
    c = await get_columns_from_csv(logday, logprefix, logdir)
    if c is None:
        logger.error(f'Log file for "{logday}" not found')
        return 1
    
    time = c['TIME']
    time_slot = (time >= start_time) & (time < stop_time)
    if time_slot.size == 0:
        logger.error(f'Major slot is empty')
        return 2

    base_mean = c[column][time_slot].mean()
    logger.info(f'The base line for comparison is "{base_mean:.0f}"')

    
    logdays = await get_logdays(
        logprefix, logdir, logdayformat)
    columns = await asyncio.gather(
        *[get_columns_from_csv(ld, logprefix, logdir) for ld in logdays])
    
    time_dict = dict((d, abs(c[column][(c['TIME']>=start_time) & (c['TIME']<stop_time)].mean() - base_mean)) \
        for (d, c) in zip(logdays, columns) if c[column] is not None)
    time_sorted = dict(sorted(time_dict.items(), key = lambda kv : kv[1]))

    time_df = pd.DataFrame(list(time_sorted.items())[1:], columns=['logday', 'closeness'])

    logger.info(f'\n{time_df.head(n=5)}')

    return 0


def hm2time(hm: str) -> t64s:
    return t64(datetime.strptime(hm, "%H:%M"))


@dataclass
class Script_Arguments:
    logday: str
    logdayformat: str
    logprefix: str
    logdir: str
    start_time: t64
    stop_time: t64
    column: str

def parse_arguments() -> Script_Arguments:
    description='Show some statistics for time slots'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)

    parser.add_argument(
        '--logday', type=str,
        help = "Day to which to find the closest")

    parser.add_argument(
        '--logdayformat', type=str,
        help = "Days to which to find the closest")
    
    parser.add_argument(
        '--logprefix', type=str,
        help = "The prefix used in log file names")

    parser.add_argument(
        '--logdir', type=str,
        help = "The directory the logfiles are stored")
    
    parser.add_argument(
        '--start_time', type=hm2time,
        help = "The start time of the slot")

    parser.add_argument(
        '--stop_time', type=hm2time,
        help = "The end time of the slot")

    parser.add_argument(
        '--column', type=str,
        help = "The col to select for major slot")

    args = parser.parse_args()
    
    return Script_Arguments(
        args.logday,
        args.logdayformat,
        args.logprefix,
        args.logdir,
        args.start_time,
        args.stop_time,
        args.column,
    )


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    err = await find_closest(**vars(args))
    
    return err


if __name__ == '__main__':
    args = parse_arguments()

    if args.stop_time <= args.start_time:
        logger.error(f'time slot is empty')
        sys.exit(1)

    if not args.column in sample_names:
        logger.error(f'column is a wrong sample name')
        sys.exit(2)
                    
    logger.info(f'solar_checker_closest_find begin')

    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
