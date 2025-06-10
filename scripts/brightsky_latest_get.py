#!/usr/bin/env python3

__doc__="""
Writes the latest inverter data to stdout
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import numpy as np

from datetime import datetime

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

from utils.common import t64_from_iso

from brightsky import Sky

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(sky: Sky, what: str) -> int:

    try:
        sunsum = None
        suncovermean = None
        if what == "sky":
            info = await sky.get_sky_info()
            sunshine = info['sunshine']
            suninfo = info[sunshine>0]
            
            sunshinetotal = suninfo['sunshine'].sum()
            suncovermean = suninfo['cloud_cover'].mean()

            info = suninfo
            
        elif what == "solar":
            info = await sky.get_solar_info()

        elif what == "sources":
            info = await sky.get_sources_info()


        # Remove time zone
        index = np.array([t64_from_iso(t[:-6]) for t in info.index])
        info.set_index(index, inplace = True)
        print(info)

        if sunshinetotal is not None:
            print(f'Total sunshine: "{sunshinetotal/60:.0f}h"')
        if suncovermean is not None:
            print(f'Mean cloud cover: "{suncovermean:.0f}%"')

        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to server.')
        err = 10
    except TypeError:
        logger.error('Unexpected exception TypeError')
        err = 11
    
    return err


@dataclass
class Script_Arguments:
    lat: float
    lon: float
    day: str
    tz: str
    what: str

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
    
    parser.add_argument('--day', type = str, default=datetime.today().strftime('%y%m%d'),
                        help = "day for forecast 'ymd'")

    parser.add_argument('--tz', type = str, default='Europe/Berlin',
                        help = "TZ for forecast")

    parser.add_argument('what', nargs='?', default='sky')

    args = parser.parse_args()

    return Script_Arguments(args.lat, args.lon, args.day, args.tz, args.what)


if __name__ == '__main__':
    args = parse_arguments()

    if args.lat < -90 or args.lat > 90:
        logger.error(f'The latitude is out of range  "{args.lat}"')
        sys.exit(1)

    if args.lon < -180 or args.lat > 180:
        logger.error(f'The longitude is out of range  "{args.lon}"')
        sys.exit(2)

    if args.day is None:
        logger.error('day for forcast is missing.')
        sys.exit(3)

    if args.what not in ['sky', 'solar', 'sources']:
        logger.error(f'Illegal command "{what}".')
        sys.exit(4)
    
    sky = Sky(args.lat,
              args.lon,
              args.day,
              args.tz)

    try:
        err = asyncio.run(main(sky, args.what))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
