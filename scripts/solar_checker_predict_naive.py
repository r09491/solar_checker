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
    predict_naive,
    get_predict_tables
)


LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'

async def output_hour(
        casthours: pd.DataFrame,
        caststart: pd.Timestamp
) -> None:
    
    pd.options.display.float_format = '{:,.1f}'.format

    predicttables = await get_predict_tables(casthours)

    w = predicttables[0]
    print(f"\nRelative Watts Cast @ {caststart}")
    print(w)

    print(f"\nAbsolute Watts Cast @ {caststart}")
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
            '--logprefix', type=str, default=LOGPREFIX,
            help = "The prefix used in log file names")

        parser.add_argument(
            '--logdir', type=str, default=LOGDIR,
            help = "The directory the logfiles are stored")
       
        args = parser.parse_args()

        return Script_Arguments(
            args.logprefix,
            args.logdir)


    async def main(args: Script_Arguments) -> int:

        cast = await predict_naive(args)
        if cast is None:
            logger.error(f'Hour Predict failed')
            return -1

        casthours, realstop, caststart = cast
        
        await output_hour(casthours, caststart)
        
        return 0

        
    try:
        err = asyncio.run(main(parse_arguments()))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
