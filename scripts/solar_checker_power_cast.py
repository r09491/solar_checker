#!/usr/bin/env python3

__doc__=""" """

__version__ = "0.0.1"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import numpy as np
import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format

from datetime import(
    datetime,
    timedelta
)

import time

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
    t64_first,
    t64_h_first,
    t64_h_last,
    t64_to_hm
)
from utils.samples import(
    get_columns_from_csv
)
from utils.weather import(
    get_sky_adapters,
    MIN_SBPB,
    MAX_SBPB,
    MAX_SBPB_CHARGING

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


async def cast_watts(
        lat: float, lon: float,
        to_day: str, from_day: str, tz: str,
        logprefix: str, logdir: str,
        skip_sun: bool = False,
        sbpi_max: int = 800
) -> Dict:

    if (to_day == from_day):
        logger.error('Cannot predict from the same days.')
        return None

    logdays = [to_day, from_day]

    # Get the df logs for the two days
    try:
        logsdf = await get_logs_from_list(
            logdays = logdays,
            logcols = PREDICT_POWER_NAMES,
            logprefix = logprefix,
            logdir = logdir)
    except AttributeError:
        logger.error('Cannot read logs')
        return None
    
    # Get the already acquired samples for the day to forecast.
    # Timestamps are normalised to the minute
    to_day_df = pd.DataFrame(
        index = [t64_first(t)
                 for t in logsdf.loc[to_day, 'TIME']],
        data = dict(logsdf.loc[to_day, PREDICT_POWER_NAMES[1:]])
    )
    
    # Separate the samples to be used for the forecast.
    # Timestamps are normalised to the minute. Date is replaced.
    from_day_df = pd.DataFrame(
        index = [ymd_over_t64(t64_first(t), to_day)
                 for t in logsdf.loc[from_day, 'TIME']],
        data = dict(logsdf.loc[from_day, PREDICT_POWER_NAMES[1:]])
    )

    # Copy the candidates for the cast
    cast_df = from_day_df.loc[to_day_df.index[-1]:].iloc[1:].copy()

    # Merge the time slots of the already acquired data with with the
    # remaining time slots of the base day. Sun adaptors not
    # considered yet
    to_day_merge_df = pd.concat(
        [to_day_df, cast_df], sort = False
    )

    if not skip_sun:
        logger.info(f'Adapting the power for the cast day to sun radiation')

        # Acquire the transformation factors
        adapters = await get_sky_adapters(
            doi = logdays, tz = tz, lat = lat, lon = lon
        )

        if adapters is None:
            logger.error('Cannot read adapters')
            return None

        # Maximum radiation before scaling. Should not be exceeded after scaling!
        max_sbpi = cast_df.loc[:,"SBPI"].max()

        # Determin the start for adaptation
        cast_h_first = t64_h_first(cast_df.index[0])
        
        # Do the cast
        for t in adapters.loc[cast_h_first:].index:
            cast_df.loc[
                t64_h_first(t):t64_h_last(t), ['SBPI']
            ] *= adapters.loc[t, "ADAPTATION"]

        # Limit sun radiation

        try:
            _smp = cast_df.loc[cast_h_first:,'SMP']
            _sbpi = cast_df.loc[cast_h_first:,'SBPI']
            _sbpo = cast_df.loc[cast_h_first:,'SBPO']            
            _sbpb = cast_df.loc[cast_h_first:,'SBPB']
            _sbsb = cast_df.loc[cast_h_first:,'SBSB']
        except KeyError:
            logger.error(f'Samples for phase "{cast_h_first}" are missing.')
            return None

        _soc = -_sbsb.iloc[0]*MAX_SBPB
        logger.info(f'"SOC is "{-_soc:.0f}Wh"')
    
        # Calculate the overall power consumption without a solarbank as
        # imported directly from the grid. For unknown reasons there may
        # be negative values which are skipped.
        _smp += _sbpo
        _smp[_smp<=0] = 0 

        # The calculated radiation has to meet system constraints of the used panel
        _sbpi[_sbpi>max_sbpi] = max_sbpi

        # There cannot be more output power then input power
        _sbpo[(_sbpi>0) & (_sbpo>_sbpi)] = _sbpi

        # Simulate the charging of the solarbank during radiation
        # Note: Discharging part will be overridden
        _sbpb[_sbpi>0] = _sbpo[_sbpi>0] - _sbpi[_sbpi>0]
        _sbpb[(_sbpi>0) & (_sbpb<-MAX_SBPB_CHARGING)] = -MAX_SBPB_CHARGING
        _sbpo[_sbpi>0] = _sbpi[_sbpi>0] + _sbpb[_sbpi>0]

        _sbpbover = (_soc + (_sbpb.cumsum()/60)) < -MAX_SBPB
        if _sbpbover.any():
            logger.info(f'OVERCHARGE: "{np.where(_sbpbover)[0][0]/60:.01f}h"')
        _sbpb[_sbpbover] = 0
        _sbpo[_sbpbover] = _sbpi[_sbpbover]
    
        _sbpbunder = (_soc + (_sbpb.cumsum()/60)) > -MIN_SBPB
        if _sbpbunder.any():
            logger.info(f'UNDERCHARGE: {np.where(_sbpbunder)[0][0]/60:0.1f}h"')
        _sbpb[_sbpbunder] = 0
        _sbpo[_sbpbunder] = 0
            
        # Reduce the needed grid power by the power from the solarbank
        _smp -= _sbpo

            
    # Concat the result for the complete day
    to_day_cast_df = pd.concat(
        [to_day_df, cast_df], sort = False
    )

    # Calc some amplyfing data
    
    issun = to_day_cast_df.loc[:,'SBPI']>0
    sun_df = to_day_cast_df.loc[issun]
    sun_first = sun_df.index[0]
    sun_last = sun_df.index[-1]

    real_last = to_day_df.index[-1]

    return {"watts_from":from_day_df,
            "watts_merge":to_day_merge_df,
            "watts_cast":to_day_cast_df,
            "sun_first":sun_first,
            "sun_last":sun_last,
            "real_last":real_last}


async def shoot_cast_watts(
        lat: float, lon: float,
        to_day: str, from_day: str, tz: str,
        logprefix: str, logdir: str,
        skip_sun:bool
) -> (pd.DataFrame, pd.DataFrame):

    cast_w = await cast_watts(
        lat, lon,
        to_day, from_day, tz,
        logprefix, logdir,
        skip_sun
    )

    if cast_w is None:
        print(f'No cast available')
        return None, None

    watts_from_df = cast_w["watts_from"].resample('H').mean() 
    watts_merge_df = cast_w["watts_merge"].resample('H').mean() 
    watts_cast_df = cast_w["watts_cast"].resample('H').mean() 

    # Every now and then some samples are missing. The 'to' is the master.

    sbpi_cast_means = watts_cast_df.loc[:,'SBPI']
    sbpb_cast_means = watts_cast_df.loc[:,'SBPB']
    sbpo_cast_means = watts_cast_df.loc[:,'SBPO']
    smp_cast_means = watts_cast_df.loc[:,'SMP']

    sbpb_cast_means_in = sbpb_cast_means.copy() 
    sbpb_cast_means_in[sbpb_cast_means>0] = 0
    sbpb_cast_means_out = sbpb_cast_means.copy() 
    sbpb_cast_means_out[sbpb_cast_means<0] = 0
    
    smp_cast_means_in = smp_cast_means.copy() 
    smp_cast_means_in[smp_cast_means<0] = 0
    smp_cast_means_out = smp_cast_means.copy() 
    smp_cast_means_out[smp_cast_means>0] = 0

    sbpi_from_means = watts_from_df.loc[:,'SBPI']
    sbpi_merge_means = watts_merge_df.loc[:,'SBPI']

    means_df = pd.DataFrame(
        data = {
            "FROM":sbpi_from_means,
            "MERGE":sbpi_merge_means,
            "CAST":sbpi_cast_means,
            ">BAT":sbpb_cast_means_in,
            "BAT>":sbpb_cast_means_out,
            "BANK":sbpo_cast_means,
            ">GRID":smp_cast_means_out,
            "GRID>":smp_cast_means_in
        }
    )

    starts = means_df.index.strftime("%H:00")
    stops = means_df.index.strftime("%H:59")
    start_stop_df =pd.DataFrame({"START":starts, "STOP":stops})

    means_df.reset_index(inplace = True, drop=True)
    
    return start_stop_df, means_df


async def main(
        lat: float, lon: float,
        to_day: str, from_day: str, tz: str,
        logprefix: str, logdir: str,
        skip_sun:bool
) -> int:

    while True:
        (start_stop_df, means_df) = await shoot_cast_watts (
            lat, lon,
            to_day, from_day, tz,
            logprefix, logdir,
            skip_sun
        )

        if ((start_stop_df is not None) and
            (means_df is not None)): 

            print()
            print(f'Power forecast per hour [W] @ {datetime.now().strftime("%H:%M:%S")}')
            print(pd.concat(
                [start_stop_df,
                 means_df
                ], axis=1))

            print()
            print(f'Energy forecast per hour [Wh] @ {datetime.now().strftime("%H:%M:%S")}')
            print(pd.concat(
                [start_stop_df,
                 means_df.cumsum()
                ], axis=1))

        else:

            print()
            print("No cast available")

        now = time.time()
        later = 300*(int(now/300) + 1)

        print()
        print(f'Next shot @ {(datetime.now() + timedelta(seconds=later-now)).strftime("%H:%M:%S")}. Please wait!')
        await asyncio.sleep(later-now)
        
    err = 0
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
    skip_sun:bool

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
                        help = "Directory of the record files")

    parser.add_argument('--skip_sun', type = int, default = 0,
                        help = "Switch to control sun adaptation")

    args = parser.parse_args()

    return Script_Arguments(
        args.lat, args.lon,
        args.to_day, args.from_day, args.tz,
        args.logprefix, args.logdir,
        args.skip_sun
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
                               args.logprefix, args.logdir,
                               args.skip_sun != 0))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
