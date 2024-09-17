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

from utils.types import t64, t64s, timeslots, Any, Optional, List
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



async def get_loglists(
        logdayformat: str,
        logprefix: str,
        logdir: str) -> list:
    
    """ Get the list of logdays """
    logdays = await get_logdays(
        logprefix, logdir, logdayformat)
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(
        *[get_columns_from_csv(ld, logprefix, logdir) for ld in logdays])
    
    return logdays, logcolumns


def get_ontimes(
        logday: str,
        logdays: list,
        logcolumns: list) -> Optional[List[t64]]:

    ilogday = logdays.index(logday)
    sbpi = logcolumns[ilogday]['SBPI']
    issbpion = sbpi>0
    if ~issbpion.any(): # no radiation
        return None, None

    time = logcolumns[ilogday]['TIME']
    timeon = time[issbpion]

    return timeon[0], timeon[-1]
    
    
async def find_closest(
        logday: str,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        starttime: t64,
        stoptime: t64,
        columns: str) -> list:

    """ Get the requested columns """
    logcols = columns.split(',')

    """ Associate the logdays with the logcolumns """
    logdays, logcolumns = await get_loglists(
        logdayformat, logprefix, logdir)
    
    """ Get the start and stop time of the radiation of the base day """

    start_ontime, stop_ontime = get_ontimes(
        logday, logdays, logcolumns)

    
    """ Override under certain conditions """
    
    starttime = hm2time("00:00") if starttime is None else \
        start_ime if start_ontime is None else \
        max(starttime, start_ontime)
    stoptime = hm2time("23:59") if stoptime is None else \
        stoptime if stop_ontime is None else \
        min(stoptime, stopontime)

    
    """ Extract the samples in watt """

    logwatts = []
    for c in [cc[:-1] if cc[-1] in "+,-" else cc for cc in logcols]:
        logwatts.append(
            [lc[c][(lc['TIME']>=starttime) & (lc['TIME']<stoptime)]
             for ld, lc in zip(logdays, logcolumns) if lc[c] is not None]
        )
    

    """ Start the log dictionary in kWh """

    logdict = {'LOGDAY': logdays}
    for c, ws in zip(logcols, logwatts):
        if c[-1] == '+':
            logdict[c] = np.array([int(w[w>0].sum()/60) for w in ws])
        elif c[-1] == '-':
            logdict[c] = np.array([int(w[w<0].sum()/60) for w in ws])
        else:
            logdict[c] = np.array([int(w.sum()/60) for w in ws])

    """ Build the state vector from the energy """
    state = logdict[logcols[0]]**2
    for c in logcols[1:]:
        state += logdict[c]**2
    logdict['STATE'] = np.array([int(v) for v in np.sqrt(state)])

    """ Check against the base state """
    logdict['CLOSENESS'] = np.array([int(v) for v in abs(
        logdict['STATE'] - logdict['STATE'][logdays.index(logday)])])

    df = pd.DataFrame(logdict)
    df.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )
    df.set_index('LOGDAY', inplace = True)
    return starttime, stoptime, df


@dataclass
class Script_Arguments:
    logday: str
    logdayformat: str
    logprefix: str
    logdir: str
    starttime: t64
    stoptime: t64
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
        '--starttime', type=hm2time, default=None,
        help = "The start time of the slot")

    parser.add_argument(
        '--stoptime', type=hm2time, default=None,
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
        args.starttime,
        args.stoptime,
        args.columns,
    )


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    starttime, stoptime, closest = await find_closest(**vars(args))
    if (starttime is None or
        stoptime is None or
        closest is None):
        print(f'No radiation detected!')
        return 1
    
    print(closest.head(n=20))

    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")
    print(f'\nUsed samples from "{start}" to "{stop}"')
    
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    if (args.stoptime is not None and
        args.starttime is not None and
        args.stoptime <= args.starttime):
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
