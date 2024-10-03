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



""" 
Print the prediction data frames. 
"""
def print_predict(
        pastwatts: pd.DataFrame,
        nowwatts: pd.DataFrame,
        predictwatts: pd.DataFrame,
        tomorrowwatts: pd.DataFrame) -> None:

    pastkwh = pastwatts.sum()/60
    pastslot = pastwatts.index.values
    paststart = pd.to_datetime(str(pastslot[0])).strftime("%H:%M")
    paststop = pd.to_datetime(str(pastslot[-1])).strftime("%H:%M")
    #print(f'\nRecorded Wh between today "{paststart}" and today "{paststop}"')
    #print(pastkwh)

    nowkwh = nowwatts.sum()/60
    nowslot = nowwatts.index.values
    nowstart = pd.to_datetime(str(nowslot[0])).strftime("%H:%M")
    nowstop = pd.to_datetime(str(nowslot[-1])).strftime("%H:%M")
    #print(f'\nRecorded Wh between today "{nowstart}" and today "{nowstop}"')
    #print(nowkwh)

    predictkwh = predictwatts.sum()/60
    predictslot = predictwatts.index.values
    predictstart = pd.to_datetime(str(predictslot[0])).strftime("%H:%M")
    predictstop = pd.to_datetime(str(predictslot[-1])).strftime("%H:%M")
    #print(f'\nPropable Wh between today "{predictstart}" and today "{predictstop}"')
    #print(predictkwh)
    
    tomorrowkwh = tomorrowwatts.sum()/60
    tomorrowslot = tomorrowwatts.index.values
    tomorrowstart = pd.to_datetime(str(tomorrowslot[0])).strftime("%H:%M")
    tomorrowstop = pd.to_datetime(str(tomorrowslot[-1])).strftime("%H:%M")
    ##print(f'\nProbable Wh between today "{tomorrowstart}" and tomorrow "{tomorrowstop}"')
    ##print(tomorrowkwh)

    print(f'\nPropable 24h Wh between today "{paststart}" and today "{predictstop}"')
    print( pastkwh + nowkwh + predictkwh)

    #print(f'\nPropable 24h Wh between today "{predictstart}" and tomorrow "{nowstop}"')
    #print( predictkwh + tomorrowkwh + nowkwh )


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
        
        ##print_predict(*predict)

        past_24 = concat_predict_24_today(*predict[:-1])
        print("\nToday Predict")
        sbpi = past_24['SBPI'].sum()/60/1000
        sbpb = past_24['SBPB'].sum()/60/1000
        ivp = (past_24['IVP1']+past_24['IVP2']).sum()/60/1000
        smp = (past_24['SMP'][past_24['SMP']>0]).sum()/60/1000
        print(f'SBPI {sbpi:.1f}kWh  SBPB {sbpb:.1f}kWh  IVP {ivp:.1f}kWh  SMP+ {smp:.1f}kWh = {ivp+smp:.1f}kWh')
        ##print(past_24.tail())
        ##print()
        #print(past_24.sum()/60)
        #print(tabulate(past_24, headers = 'keys', tablefmt = 'grid'))

        #tomorrow_24 = concat_predict_24_tomorrow(*predict[1:])
        #print("\nTomorrow Predict")
        #print(tomorrow_24.tail())
        #print()
        ##print(tomorrow_24.sum()/60)
        #print(tabulate(tomorrow_24, headers = 'keys', tablefmt = 'grid'))
    
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
