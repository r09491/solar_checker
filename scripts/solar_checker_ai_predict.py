#!/usr/bin/env python3

__doc__="""Predict samples for a day with an AI model
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import os
import sys
import argparse
import asyncio
import joblib

import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

from dataclasses import dataclass

from aicast.predict_models import (
    predict_models
)

from datetime import (
    datetime,
    timedelta
)

DAY=(datetime.today()+timedelta(days=1)).strftime('%y%m%d')

LAT, LON, TZ = 49.04885, 11.78333, 'Europe/Berlin'

CASTSDIR='/mnt/fritz/SOLAR_CHECKER/aicast/casts'
MODELDIR='/mnt/fritz/SOLAR_CHECKER/aicast/models'

@dataclass
class Script_Arguments:
    day:str
    tz:str
    lat:float
    lon:float
    modeldir:str
    castsdir:str

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Predict PV samples based on KI models',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument(
        '--day', type = str, default=DAY,
        help = "day of forecast in 'ymd'")
    
    parser.add_argument(
        '--tz', type = str, default=TZ,
        help = "TZ for forecast"
    )
    parser.add_argument(
        '--lat', type = float, default = LAT,
        help = "latitude for forecast [-90 - +90]"
    )
    parser.add_argument(
        '--lon', type = float, default = LON,
        help = "longitude for forecast [-180 - +180]"
    )
    parser.add_argument(
        '--modeldir', type=str, default=MODELDIR,
        help = "The directory where the models are stored"
    )    
    parser.add_argument(
        '--castsdir', type=str, default=CASTSDIR,
        help = "The directory to store the predicts in"
    )    

    args = parser.parse_args()

    return Script_Arguments(
        args.day,
        args.tz,
        args.lat,
        args.lon,
        args.modeldir,
        args.castsdir
    )


async def shoot_pool_watts(
        pool: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    if pool is None:
        print(f'No cast available')
        return None, None

    pool.set_index('TIME', inplace=True)
    
    means = pool.resample('h').mean() 

    sbpi_means = means.loc[:,'SBPI']
    sbpb_means = means.loc[:,'SBPB']
    sbpo_means = means.loc[:,'SBPO']
    smp_means = means.loc[:,'SMP']

    sbpb_means_in = sbpb_means.copy() 
    sbpb_means_in[sbpb_means>0] = 0
    sbpb_means_out = sbpb_means.copy() 
    sbpb_means_out[sbpb_means<0] = 0
    
    smp_means_in = smp_means.copy() 
    smp_means_in[smp_means<0] = 0
    smp_means_out = smp_means.copy() 
    smp_means_out[smp_means>0] = 0

    means_df = pd.DataFrame(
        data = {
            "SBPI":sbpi_means,
            ">SBPB":sbpb_means_in,
            "SBPB>":sbpb_means_out,
            "SBPO":sbpo_means,
            ">SMP":smp_means_out,
            "SMP>":smp_means_in
        }
    )

    starts = means_df.index.strftime("%H:00")
    stops = means_df.index.strftime("%H:59")
    start_stop_df =pd.DataFrame({"START":starts, "STOP":stops})

    means_df.reset_index(inplace = True, drop=True)
    
    return start_stop_df, means_df

async def main(
        day:str,
        tz:str,
        lat:str,
        lon:str,
        modeldir:str,
        castsdir:str,
):

    logger.info(f'Cast for day "{day}"')
    
    pool = await predict_models(
        day, tz, lat, lon, modeldir
    )

    if pool is None:
        logger.error(f'Cast for day "{day}" failed')
        return -1

    pool.to_csv(f'{castsdir}/cast_{day}.csv')
    logger.info(f'Saved cast to "{castsdir}/cast_{day}.csv"')

    (start_stop_df, means_df) = await shoot_pool_watts(pool)
    if ((start_stop_df is None) or
        (means_df is None)
        ): 
        logger.error(f'Cannot print hourly pool data')
        return -2

    print()
    print(f'Power forecast per hour [W]')
    print(pd.concat([start_stop_df, means_df], axis=1))

    print()
    print(f'Energy forecast per hour [Wh]')
    print(pd.concat([start_stop_df, means_df.cumsum()], axis=1))

    print()
    
    return 0

if __name__ == "__main__":
    args = parse_arguments()

    if args.lat < -90 or args.lat > 90:
        logger.error(f'The latitude is out of range  "{args.lat}"')
        sys.exit(1)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'The longitude is out of range  "{args.lon}"')
        sys.exit(2)

    try:
        err = asyncio.run(
            main(
                args.day,
                args.tz,
                args.lat,
                args.lon,
                args.modeldir,
                args.castsdir,
            )
        )
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
