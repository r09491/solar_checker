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
pd.options.display.float_format = '{:,.1f}'.format
        
from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.typing import (
    t64, f64, Any, Optional, List, Dict
)
from utils.common import (
    PREDICT_NAMES,
    POWER_NAMES,
    PARTITION_NAMES
)
from utils.common import (
    hm_to_t64,
    t64_to_hm
)
from utils.weather import (
    get_sky_adapters,
    apply_sky_adapters,
)
from utils.predicts import (
    get_logs_as_dataframe,
    find_closest,
    partition_closest_watts,
    get_predict_table,
    concat_today,
    concat_tomorrow,
    concat_total
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


""" 
Print the prediction data frames. 
"""
def print_predict(
        predicttable: pd.DataFrame,
        batpercent: f64) -> None:

    pd.options.display.float_format = '{:,.1f}'.format

    print("\nRelative Watts")
    print(predicttable)

    print("\nAbsolute Watts")
    awatts = pd.concat([predicttable.iloc[:,:2],
                        predicttable.iloc[:,2:].cumsum()]
                       , axis=1)
    awatts['START'] = '00:00'
    print(awatts)
    print()

TODAY=datetime.today().strftime('%y%m%d')
    
LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'
LOGDAYFORMAT='*'

LAT, LON, TZ = 49.04885, 11.78333, 'Europe/Berlin'
     
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
    predictdays: int
    columns: str
    lat: f64
    lon: f64
    tz: str
    

def parse_arguments() -> Script_Arguments:
    description='Find a list of the closest log files for the given basefile'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)

    parser.add_argument(
        '--logday', type=str, default=TODAY,
        help = "Day to which to find the closest")

    parser.add_argument(
        '--logmaxdays', type=int, default=50,
        help = "Days to which to find the closest")

    parser.add_argument(
        '--logdayformat', type=str, default=LOGDAYFORMAT,
        help = "Days to which to find the closest")
    
    parser.add_argument(
        '--logprefix', type=str, default=LOGPREFIX,
        help = "The prefix used in log file names")

    parser.add_argument(
        '--logdir', type=str, default=LOGDIR,
        help = "The directory the logfiles are stored")
    
    parser.add_argument(
        '--starttime', type=hm_to_t64, default=None,
        help = "The start time of the slot")

    parser.add_argument(
        '--stoptime', type=hm_to_t64, default=None,
        help = "The end time of the slot")

    parser.add_argument(
        '--predict', type=bool, default=False,
        help = "Disable/Enable prediction")

    parser.add_argument(
        '--predictdays', type=int, default=3,
        help = "The number of days - 1 used for prediction")

    parser.add_argument(
        '--columns', type=str, required = True,
        help = "The list names of the to be used. The first determines the time slot for the evaluation an prediction"
    )

    parser.add_argument('--lat', type = float, default=LAT,
                        help = "latitude for forecast [-90 - +90]")

    parser.add_argument('--lon', type = float, default=LON,
                        help = "longitude for forecast [-180 - +180]")
        
    parser.add_argument('--tz', type = str, default=TZ,
                        help = "TZ for forecast")

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
        args.predictdays,
        args.columns,
        args.lat,
        args.lon,
        args.tz
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
        logsdf, args.logday,
        args.starttime,
        args.stoptime,
        args.columns
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
        todaydoi, tomorrowdoi, soc, partitions = await partition_closest_watts(
            logsdf,
            starttime,
            stoptime,
            closestdays.head(n=args.predictdays),
        )

        todayadapters, tomorrowadapters = await asyncio.gather(
            get_sky_adapters(todaydoi, args.lat, args.lon, args.tz),
            get_sky_adapters(tomorrowdoi, args.lat, args.lon, args.tz)
        )


        """ Apply adapters to all phases with radiation """
        
        apply_sky_adapters(
            partitions, 'todaywatts', todayadapters)
        apply_sky_adapters(
            partitions, 'tomorrowwatts1', tomorrowadapters)
        apply_sky_adapters(
            partitions, 'tomorrowwatts2', tomorrowadapters)
        
        print_predict(*get_predict_table(partitions))


        ensemble_time = args.logday + stop[:2]
        ensembles_dir = os.path.join(args.logdir, 'ensembles')
        if os.path.isdir(os.path.join(ensembles_dir)):
            today_watts = concat_today(partitions)
            today_watts_csv = os.path.join(ensembles_dir,
                                           f'watts_today_{ensemble_time}.csv')
            today_watts.to_csv(today_watts_csv,
                               encoding='utf-8',
                               index=True, index_label='TIME',
                               header=True, columns=PARTITION_NAMES,
                               float_format='%.0f')
            print(f'Saved today watts to "{today_watts_csv}"')

            tomorrow_watts = concat_tomorrow(partitions)
            tomorrow_watts_csv = os.path.join(ensembles_dir,
                                              f'watts_tomorrow_{ensemble_time}.csv')
            tomorrow_watts.to_csv(tomorrow_watts_csv,
                                  encoding='utf-8',
                                  index=True, index_label='TIME',
                                  header=True, columns=PARTITION_NAMES,
                                  float_format='%.0f')
            print(f'Saved tomorrow watts to "{tomorrow_watts_csv}"')

            total_watts = concat_total(partitions)
            total_watts_csv = os.path.join(ensembles_dir,
                                           f'watts_total_{ensemble_time}.csv')
            total_watts.to_csv(total_watts_csv,
                               encoding='utf-8',
                               index=True, index_label='TIME',
                               header=True, columns=PARTITION_NAMES,
                               float_format='%.0f')
            print(f'Saved total watts to "{total_watts_csv}"')
        
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

    if args.lat < -90 or args.lat > 90:
        logger.error(f'latitude is out of range  "{args.lat}"')
        sys.exit(4)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'longitude is out of range  "{args.lon}"')
        sys.exit(5)
            
    logger.info(f'solar_checker_closest_find begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
