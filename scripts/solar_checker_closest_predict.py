#!/usr/bin/env python3

__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

#from tabulate import tabulate

import numpy as np
import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format
        
from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.types import (
    t64, Any, Optional, List, Dict
)
from utils.common import (
    PREDICT_NAMES,
    POWER_NAMES
)
from utils.common import (
    hm2time
)
from utils.predicts import (
    get_logs_as_dataframe,
    find_closest,
    predict_closest,
    concat_predict_24_today,
    concat_predict_24_tomorrow
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))



def t2hm(t: t64) -> str:
    return pd.to_datetime(str(t)).strftime("%H:%M")

""" 
Print the prediction data frames. 
"""
def print_predict(
        prewatts: pd.DataFrame,
        findwatts: pd.DataFrame,
        postwatts: pd.DataFrame,
        predictwatts: pd.DataFrame) -> None:


    input = vars()

    phase = [k for (k,v) in input.items() if len(v) >0]
    start = [t2hm(v.index.values[0]) for (k,v) in input.items() if v.size >0]
    stop = [t2hm(v.index.values[-1]) for (k,v) in input.items() if v.size >0]
    watts = pd.concat([v.sum()/60 for (k,v) in input.items() if v.size >0], axis=1)

    wattphases = pd.concat(
        [pd.DataFrame(
            {'PHASE':phase,
             'START': start,
             'STOP': stop}), watts.T
        ], sort=False, axis=1)
    wattphases.set_index('PHASE', inplace=True)

    print(f'\nPhases:\n{wattphases}')

    watttotal = pd.DataFrame(wattphases.iloc[:,2:].sum(axis=0))
    print(f'\nTotal:\n{watttotal.T}\n')

    

@dataclass
class Script_Arguments:
    logday: str
    logmaxdays: int
    logdayformat: str
    logprefix: str
    logdir: str
    starttime: t64
    stoptime: t64
    predict: bool
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
        '--logmaxdays', type=int, default=50,
        help = "Days to which to find the closest")

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
        '--predict', type=bool, default=False,
        help = "Disable/Enable prediction")

    parser.add_argument(
        '--columns', type=str,
        help = "The list names of the to be used. The first determines the time slot for the evaluation an prediction"
    )

    args = parser.parse_args()
    
    return Script_Arguments(
        args.logday,
        args.logmaxdays,
        args.logdayformat,
        args.logprefix,
        args.logdir,
        args.starttime,
        args.stoptime,
        args.predict,
        args.columns,
    )


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    """ Get the dictionary with all the power recordings per logdays """
    logsdf = await get_logs_as_dataframe(
        POWER_NAMES,
        args.logmaxdays,
        args.logdayformat,
        args.logprefix,
        args.logdir
    )

    starttime, stoptime, closestdays = await find_closest(
        logsdf, args.logday, args.starttime, args.stoptime, args.columns
    )
    if (starttime is None or
        stoptime is None or
        closestdays is None):
        print(f'No radiation for the log day detected!')
        return 1
    
    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")
    print(f'Using watt samples from "{start}" to "{stop}"')

    print(closestdays.head(n=10))

    if args.predict:
        predict = await predict_closest(
            logsdf, starttime, stoptime, closestdays.head(n=4)
        )

        pd.options.display.float_format = '{:,.1f}'.format
        print_predict(*predict[:-1]) # Without tomorrow
    
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    if (args.stoptime is not None and
        args.starttime is not None and
        args.stoptime <= args.starttime):
        logger.error(f'time slot is empty')
        sys.exit(1)

    for c in args.columns.split(','):
        if not c in PREDICT_NAMES:
            print(f'"{c}" is a wrong sample name')
            sys.exit(2)

    if args.columns.split(',')[0][-1] in ['-']:
            print(f'first column must not have extension')
            sys.exit(3)
            
    logger.info(f'solar_checker_closest_find begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
