#!/usr/bin/env python3

__doc__=""" Train an AI model on PV samples to predict PV samples for a day
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

from dataclasses import dataclass

from aicast.train_models import (
    train_models
)

MODELDIR='/home/r09491/storage/solar_checker/aicast/models'

LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'
LOGDAYFORMAT='*'

LAT, LON, TZ = 49.04885, 11.78333, 'Europe/Berlin'

@dataclass
class Script_Arguments:
    modeldir:str
    logdir:str
    logprefix:str
    logdayformat:str
    tz:str
    lat:float
    lon:float

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest weather forecast transformation factors',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument(
        '--modeldir', type=str, default=MODELDIR,
        help = "The directory to store the models in"
    )    
    parser.add_argument(
        '--logdir', type=str, default=LOGDIR,
        help = "The directory the logfiles are stored in"
    )
    parser.add_argument(
        '--logprefix', type=str, default=LOGPREFIX,
        help = "The prefix used in log file names"
    )
    parser.add_argument(
        '--logdayformat', type=str, default=LOGDAYFORMAT,
        help = "Days to select files for the pools"
    )
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

    args = parser.parse_args()

    return Script_Arguments(
        args.modeldir,
        args.logdir,
        args.logprefix,
        args.logdayformat,
        args.tz,
        args.lat,
        args.lon)


async def main(
        modeldir:str,
        logdir:str,
        logprefix:str,
        logdayformat:str,
        tz:str,
        lat:str,
        lon:str
):

    models = await train_models(
        logdir, logprefix, logdayformat, tz, lat, lon
    )

    if models is None:
        logger.error('Unable to train models')
        return -1

    ##[sbpi_model, sbsb_model, sbpb_model, smp_model] = models
    [sbpi_model, sbpb_model, smp_model] = models
    joblib.dump(sbpi_model, f'{modeldir}/lightgbm_sbpi_model.pkl')
    logger.info(f'Model saved as "{modeldir}/lightgbm_sbpi_model.pkl"')
    ##joblib.dump(sbsb_model, f'{modeldir}/lightgbm_sbsb_model.pkl')
    ##logger.info(f'Model saved as "{modeldir}/lightgbm_sbsb_model.pkl"')
    joblib.dump(sbpb_model, f'{modeldir}/lightgbm_sbpb_model.pkl')
    logger.info(f'Model saved as "{modeldir}/lightgbm_sbpb_model.pkl"')
    joblib.dump(smp_model, f'{modeldir}/lightgbm_smp_model.pkl')
    logger.info(f'Model saved as "{modeldir}/lightgbm_smp_model.pkl"')

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
                args.modeldir,
                args.logdir,
                args.logprefix,
                args.logdayformat,
                args.tz,
                args.lat,
                args.lon
            )
        )
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
