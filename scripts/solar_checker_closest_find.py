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

        
async def find_closest(
        logday: str,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        start_time: t64,
        stop_time: t64,
        columns: str) -> Any:

    logdays = await get_logdays(
        logprefix, logdir, logdayformat)
    logcolumns = await asyncio.gather(
        *[get_columns_from_csv(ld, logprefix, logdir) for ld in logdays])

    """ Get the energy for the samples in the given time slot"""
    logcols = columns.split(',')

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
    logdict['CLOSENESS'] = np.array([int(v) for v in abs(logdict['STATE'] - logdict['STATE'][-1])])

    logdf = pd.DataFrame(logdict)
    logdf.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )
    logdf.set_index('LOGDAY', inplace = True)
    return logdf


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
        '--start_time', type=hm2time,
        help = "The start time of the slot")

    parser.add_argument(
        '--stop_time', type=hm2time,
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

    closest = await find_closest(**vars(args))
    print(closest.head(n=20))

    start = args.start_time.astype(datetime).strftime("%H:%M")
    stop = args.stop_time.astype(datetime).strftime("%H:%M")
    print(f'\nUsed samples from "{start}" to "{stop}"')
    
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    if args.stop_time <= args.start_time:
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
