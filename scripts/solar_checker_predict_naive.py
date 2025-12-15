#!/usr/bin/env python3

__doc__="""
Writes a prediction table for the rest of today estimating the irridance and using a solarbank model dependent on the irridiance.
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

import numpy as np
import pandas as pd

from dataclasses import dataclass

from utils.typing import(
    List, Optional
)
from utils.predicts import (
    Script_Arguments,
    predict_naive_today,
    predict_naive_castday,
    get_predict_tables
)


LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'

async def output_hour(
        castday:str,
        casthours: pd.DataFrame,
        caststart: pd.Timestamp
) -> None:
    
    pd.options.display.float_format = '{:,.1f}'.format

    predicttables = await get_predict_tables(casthours)

    w = predicttables[0]
    print(f"\nRelative Watts [W] Cast @ {caststart} for {castday}")
    print(w)

    print(f"\nAbsolute Watts [Wh] Cast @ {caststart} for {castday}")
    wh =  predicttables[1]
    print(wh)
    
    print()


if __name__ == '__main__':
    def parse_arguments() -> Script_Arguments:
        """Parse command line arguments"""

        parser = argparse.ArgumentParser(
            prog=os.path.basename(sys.argv[0]),
            description='Get the latest weather forecast',
            epilog=__doc__)

        parser.add_argument('--version', action = 'version', version = __version__)

        parser.add_argument(
            '--castday', type=str, default=None,
            help = "The day to predict. If 'None' then today!")

        parser.add_argument(
            '--lat', type = float, default = 49.04885,
            help = "latitude for predict [-90 - +90]")

        parser.add_argument(
            '--lon', type = float, default = 11.78333,
            help = "longitude for predict [-180 - +180]")

        parser.add_argument(
            '--logprefix', type=str, default=LOGPREFIX,
            help = "The prefix used in log file names")

        parser.add_argument(
            '--logdir', type=str, default=LOGDIR,
            help = "The directory the logfiles are stored")
       
        args = parser.parse_args()

        return Script_Arguments(
            args.castday,
            args.lat,
            args.lon,
            args.logprefix,
            args.logdir)


    async def main(args: Script_Arguments) -> int:

        if args.castday is None:
            cast = await predict_naive_today(
                args.lat,
                args.lon,
                args.logprefix,
                args.logdir
            )
            if cast is None:
                logger.error(f'Today Predict failed')
                return -1

            castday, casthours, _, caststart = cast
            
        else:
            cast = await predict_naive_castday(
                args.castday,
                args.lat,
                args.lon,
                args.logprefix,
                args.logdir
            )
            if cast is None:
                logger.error(f'Castday predict failed')
                return -2

            castday, casthours, _, caststart = cast
        
        await output_hour(castday, casthours, caststart)

        return 0

        
    try:
        err = asyncio.run(main(parse_arguments()))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
