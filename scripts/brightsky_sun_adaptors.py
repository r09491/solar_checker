#!/usr/bin/env python3

__doc__=""" Prints the adaptors K to predict the power P0 at day0 from
the power P1 at day1 based on their individual hourly sun durations T
(P0 = K*P1, K = 1 + (T0-T1)/60) """

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

from datetime import datetime

from utils.predicts import get_sun_adaptors

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(day0: str, day1: str, tz: str, lat: float, lon: float) -> int:

    try:
        adaptors = await get_sun_adaptors(
            doi = [day0, day1], tz = tz, lat = lat, lon = lon
        )
        print(adaptors)

        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to server.')
        err = 1
    except TypeError:
        logger.error('Unexpected exception TypeError')
        err = 2
    
    return err


@dataclass
class Script_Arguments:
    lat: float
    lon: float
    day0: str
    day1: str
    tz: str

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest weather forecast',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--lat', type = float, default = 49.04885,
                        help = "latitude for forecast [-90 - +90]")

    parser.add_argument('--lon', type = float, default = 11.78333,
                        help = "longitude for forecast [-180 - +180]")
    
    parser.add_argument('--day0', type = str, required = True,
                        help = "day0 for compare 'ymd'")

    parser.add_argument('--day1', type = str, required = True,
                        help = "day1 for compare 'ymd'")

    parser.add_argument('--tz', type = str, default='Europe/Berlin',
                        help = "TZ for forecast")

    args = parser.parse_args()

    return Script_Arguments(args.lat, args.lon, args.day0, args.day1, args.tz)


if __name__ == '__main__':
    args = parse_arguments()

    if args.lat < -90 or args.lat > 90:
        logger.error(f'The latitude is out of range  "{args.lat}"')
        sys.exit(1)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'The longitude is out of range  "{args.lon}"')
        sys.exit(2)

    if args.day0 is None:
        logger.error('day0 for compare is missing.')
        sys.exit(3)

    if args.day1 is None:
        logger.error('day1 for compare is missing.')
        sys.exit(4)        
    
    try:
        err = asyncio.run(main(args.day0, args.day1, args.tz, args.lat, args.lon))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
