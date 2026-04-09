#!/usr/bin/env python3

__doc__="""
Finds the best ratio parameters for predict naive
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
    predict_naive_check
)


LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'

async def output_result(
        result: pd.Dataframe,
) -> None:
    
    pd.options.display.float_format = '{:,.0f}'.format
    
    print(result)
    

if __name__ == '__main__':
    def parse_arguments() -> Script_Arguments:
        """Parse command line arguments"""

        parser = argparse.ArgumentParser(
            prog=os.path.basename(sys.argv[0]),
            description='Get the latest weather forecast',
            epilog=__doc__)

        parser.add_argument('--version', action = 'version', version = __version__)

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
            help = "The directory the logfiles are stored in")
       
        args = parser.parse_args()

        return Script_Arguments(
            None,
            args.lat,
            args.lon,
            args.logprefix,
            args.logdir)


    async def main(args: Script_Arguments) -> int:

        result = await predict_naive_check(
            args.lat,
            args.lon,
            args.logprefix,
            args.logdir
        )
        if result is None:
            logger.error(f'Check results failed')
            return -1

        await output_result(result)
        
        return 0

        
    try:
        err = asyncio.run(main(parse_arguments()))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
