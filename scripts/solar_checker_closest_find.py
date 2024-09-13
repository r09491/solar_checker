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
from utils.samples import get_columns_from_csv
from utils.samples import get_logdays


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

"""
Only power samples may be used. For some sanmple it is possible to
split between positive and negative values.
"""
POWER_NAMES = [
    'SMP', 'SMP+', 'SMP-', 
    'IVP1',
    'IVP2',
    'SPPH',
    'SBPI', 'SBPO', 'SBPB', 'SBPB+','SBPB-',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]


def hm2time(hm: str) -> t64s:
    return t64(datetime.strptime(hm, "%H:%M"))


async def find_closest(
        logday: str,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        start_time: t64,
        stop_time: t64,
        columns: str) -> list:

    """ Get the requested samples """
    logcols = columns.split(',')

    """ Get the list of logdays """
    logdays = await get_logdays(
        logprefix, logdir, logdayformat)
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(
        *[get_columns_from_csv(ld, logprefix, logdir) for ld in logdays])


    """ Get the start and stop time of the radiation of the base day """

    ilogday = logdays.index(logday)
    sbpi = logcolumns[ilogday]['SBPI']
    issbpion = sbpi>0
    if issbpion.any(): # radiation

        time = logcolumns[ilogday]['TIME']
        timeon = time[issbpion]

        start_time = timeon[0] if start_time is None else max(timeon[0], start_time)
        stop_time = timeon[-1] if stop_time is None else min(timeon[-1], stop_time)

    else: # no radiation

        start_time = hm2time("00:00") if start_time is None else start_time
        stop_time =  hm2time("23:59") if stop_time is None else stop_time

        
    """ Extract the samples in watt """

    logsamples = []
    for c in [cc[:-1] if cc[-1] in "+,-" else cc for cc in logcols]:
        logsamples.append(
            [lc[c][(lc['TIME']>=start_time) & (lc['TIME']<stop_time)]
             for ld, lc in zip(logdays, logcolumns) if lc[c] is not None]
        )
    

    """ Start the log dictionary in kWh """

    logdict = {'LOGDAY': logdays}
    for c, s in zip(logcols, logsamples):
        if c[-1] == '+':
            logdict[c] = np.array([int(kw[kw>0].sum()/60) for kw in s])
        elif c[-1] == '-':
            logdict[c] = np.array([int(kw[kw<0].sum()/60) for kw in s])
        else:
            logdict[c] = np.array([int(kw.sum()/60) for kw in s])

    """ Build the state vector from the energy """
    state = logdict[logcols[0]]**2
    for c in logcols[1:]:
        state += logdict[c]**2
    logdict['STATE'] = np.array([int(v) for v in np.sqrt(state)])

    """ Check against the base state """
    logdict['CLOSENESS'] = np.array([int(v) for v in abs(logdict['STATE'] - logdict['STATE'][ilogday])])

    df = pd.DataFrame(logdict)
    df.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )
    df.set_index('LOGDAY', inplace = True)
    return start_time, stop_time, df


@dataclass
class Script_Arguments:
    logday: str
    logdayformat: str
    logprefix: str
    logdir: str
    start_time: t64
    stop_time: t64
    columns: str

def parse_arguments() -> Script_Arguments:
    description='Find a list of the closest log files for the given basefile'
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
        '--start_time', type=hm2time, default=None,
        help = "The start time of the slot")

    parser.add_argument(
        '--stop_time', type=hm2time, default=None,
        help = "The end time of the slot")

    parser.add_argument(
        '--columns', type=str,
        help = "The col to select for major slot")

    args = parser.parse_args()
    
    return Script_Arguments(
        args.logday,
        args.logdayformat,
        args.logprefix,
        args.logdir,
        args.start_time,
        args.stop_time,
        args.columns,
    )


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    start_time, stop_time, closest = await find_closest(**vars(args))
    if (start_time is None or
        stop_time is None or
        closest is None):
        print(f'No radiation detected!')
        return 1
    
    print(closest.head(n=20))

    start = pd.to_datetime(str(start_time)).strftime("%H:%M")
    stop = pd.to_datetime(str(stop_time)).strftime("%H:%M")
    print(f'\nUsed samples from "{start}" to "{stop}"')
    
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    if (args.stop_time is not None and
        args.start_time is not None and
        args.stop_time <= args.start_time):
        logger.error(f'time slot is empty')
        sys.exit(1)

    for c in args.columns.split(','):
        if not c in POWER_NAMES:
            logger.error(f'column is a wrong sample name')
            sys.exit(2)
                    
    logger.info(f'solar_checker_closest_find begin')

    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
