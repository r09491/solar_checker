#!/usr/bin/env python3

__doc__=""" Prints the adaptors K to predict the power P0 at the
target day 'to_day' (T0)from the power P1 at the source day 'from_day'
(T1) based on their individual hourly sun durations T (P0 = K*P1, K =
1 + (T0-T1)/60). It is assumed that the power produced
increases/decreases linear with the sun duration. """

__version__ = "0.0.1"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

from datetime import(
    datetime,
    timedelta
)

from utils.weather import get_sun_adapters

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(to_day: str, from_day: str, tz: str, lat: float, lon: float) -> int:

    try:
        adaptors = await get_sun_adapters(
            doi = [to_day, from_day], tz = tz, lat = lat, lon = lon
        )
        print(f'Adapters from day "{from_day}" to day "{to_day}"')
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
    to_day: str
    from_day: str
    tz: str

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
    
    parser.add_argument('--to_day', type = str, default=datetime.today().strftime('%y%m%d'),
                        help = "day for transformation in 'ymd'")

    parser.add_argument('--from_day', type = str, default=(datetime.today()-timedelta(days=1)).strftime('%y%m%d'),
                        help = "day of sun forecast in 'ymd'")

    parser.add_argument('--tz', type = str, default='Europe/Berlin',
                        help = "TZ for forecast")

    args = parser.parse_args()

    return Script_Arguments(args.lat, args.lon, args.to_day, args.from_day, args.tz)


if __name__ == '__main__':
    args = parse_arguments()

    if args.lat < -90 or args.lat > 90:
        logger.error(f'The latitude is out of range  "{args.lat}"')
        sys.exit(1)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'The longitude is out of range  "{args.lon}"')
        sys.exit(2)

    if args.to_day is None:
        logger.error('to_day is missing.')
        sys.exit(3)

    if args.from_day is None:
        logger.error('from_day is missing.')
        sys.exit(4)        
    
    try:
        err = asyncio.run(main(args.to_day, args.from_day, args.tz, args.lat, args.lon))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
