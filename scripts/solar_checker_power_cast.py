#!/usr/bin/env python3

__doc__=""" """

__version__ = "0.0.1"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format

from datetime import datetime

from dataclasses import dataclass

from aiohttp.client_exceptions import ClientConnectorError

from utils.typing import(
    List, Dict
)
from utils.common import(
    PREDICT_POWER_NAMES
)
from utils.common import(
    ymd_over_t64,
    t64_h_first,
    t64_h_last
)
from utils.samples import(
    get_columns_from_csv
)
from utils.casts import(
    get_sun_adapters
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

""" Get the list of logdays and the list of dictionaries with all the
recordings """
async def get_logs_from_list(
        logdays: List,
        logcols: List,
        logprefix: str,
        logdir: str) -> pd.DataFrame:

    logtasks = [asyncio.create_task(
        get_columns_from_csv(
            ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(*logtasks)

    return pd.DataFrame(index = logdays, data=logcolumns)[logcols]


async def get_w_cast(
        lat: float, lon: float,
        to_day: str, from_day: str, tz: str,
        logprefix: str, logdir: str
) -> Dict:

    logdays = [to_day, from_day]

    # Get the df logs for the two days
    logsdf = await get_logs_from_list(
        logdays = logdays,
        logcols = PREDICT_POWER_NAMES,
        logprefix = logprefix,
        logdir = logdir)

    # Separate the acquired samples for the day to forecast 
    to_day_df = pd.DataFrame(
        index = logsdf.loc[to_day, 'TIME'],
        data = dict(logsdf.loc[to_day, PREDICT_POWER_NAMES[1:-1]])
    )

    # Separate the samples to be used for the forecast
    from_day_df = pd.DataFrame(
        index = [ymd_over_t64(t, to_day) for t in logsdf.loc[from_day, 'TIME']],
        data = dict(logsdf.loc[from_day, PREDICT_POWER_NAMES[1:-1]])
    )

    # Acquire the transformation factors
    adapters = await get_sun_adapters(
            doi = logdays, tz = tz, lat = lat, lon = lon
    )

    # Determine the candidates for the cast
    cast_df = from_day_df.loc[to_day_df.index[-1]:].iloc[1:]

    # Do the cast
    for t in adapters.index[:-1]:
        cast_df.loc[t64_h_first(t):t64_h_last(t),
                    ['SBPI', 'SBPO', 'SBPB']][:-1] *= adapters.loc[t]
        
    # Concat the result for the complete day
    result_df = pd.concat(
        [to_day_df, cast_df], sort = False
    )

    # Calc some amplyfing data
    
    issun = result_df.loc[:,'SBPI']>0
    sun_df = result_df.loc[issun]
    sun_first = sun_df.index[0]
    sun_last = sun_df.index[-1]

    real_last = to_day_df.index[-1]

    return {"watts":result_df,
            "sun_first":sun_first,
            "sun_last":sun_last,
            "real_last":real_last}


async def main(
        lat: float, lon: float,
        to_day: str, from_day: str, tz: str,
        logprefix: str, logdir: str
) -> int:

    w_cast = await get_w_cast(
        lat, lon,
        to_day, from_day, tz,
        logprefix, logdir
    )

    watts_df = w_cast["watts"]

    sun_first = w_cast["sun_first"]
    real_last = w_cast["real_last"]
    sun_df = watts_df.loc[sun_first:real_last]

    sun_mtimes = sun_df.index
    sun_htimes = [sun_mtimes[t] for t in range(0, len(sun_mtimes), 60)]
    sun_means = [sun_df.loc[t64_h_first(h):t64_h_last(h)].mean(axis=0) for h in sun_htimes]
    sun_means_df = pd.DataFrame(index = sun_htimes, data = sun_means)
    print("Watts forecast during sunshine per hour [Wh]")
    print(sun_means_df)
    print("Total [Wh]")
    print(sun_means_df.sum())

    err = 0
    
    """
    try:

        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to server.')
        err = 1
    except TypeError:
        logger.error('Unexpected exception TypeError')
        err = 2
    """
    
    return err


@dataclass
class Script_Arguments:
    lat: float
    lon: float
    to_day: str
    from_day: str
    tz: str
    logprefix:str
    logdir:str

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest weather forecast transformation factors',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--lat', type = float, default = 49.04885,
                        help = "latitude for forecast [-90 - +90]")

    parser.add_argument('--lon', type = float, default = 11.78333,
                        help = "longitude for forecast [-180 - +180]")
    
    parser.add_argument('--to_day', type = str, required = True,
                        help = "day for transformation in 'ymd'")

    parser.add_argument('--from_day', type = str, required = True,
                        help = "day of sun forecast in 'ymd'")

    parser.add_argument('--tz', type = str, default='Europe/Berlin',
                        help = "TZ for forecast")

    parser.add_argument('--logprefix', type = str, required = True,
                        help = "Prefix of the record file'")

    parser.add_argument('--logdir', type = str, required = True,
                        help = "Directory of the record files'")

    args = parser.parse_args()

    return Script_Arguments(
        args.lat, args.lon,
        args.to_day, args.from_day, args.tz,
        args.logprefix, args.logdir
    )


if __name__ == '__main__':
    args = parse_arguments()

    if args.lat < -90 or args.lat > 90:
        logger.error(f'The latitude is out of range  "{args.lat}"')
        sys.exit(-1)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'The longitude is out of range  "{args.lon}"')
        sys.exit(-2)

    if args.to_day is None:
        logger.error('to_day is missing.')
        sys.exit(-3)

    if args.from_day is None:
        logger.error('from_day is missing.')
        sys.exit(-4)        
    
    if args.logprefix is None:
        logger.error('log prefix is missing.')
        sys.exit(-5)        

    if args.logdir is None:
        logger.error('log dir is missing.')
        sys.exit(-6)        

    try:
        err = asyncio.run(main(args.lat, args.lon,
                               args.to_day, args.from_day, args.tz,
                               args.logprefix, args.logdir))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
