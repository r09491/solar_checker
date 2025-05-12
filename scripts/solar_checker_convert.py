#!/usr/bin/env python3

__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

#from tabulate import tabulate

import numpy as np
import pandas as pd
pd.options.display.float_format = '{:,.1f}'.format
        
from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.typing import (
    t64, f64, Any, Optional, List, Dict
)
from utils.common import (
    hm_to_t64
)
from utils.samples import (
    get_columns_from_csv
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

@dataclass
class Script_Arguments:
    logday: str
    logprefix: str
    logdir: str

def parse_arguments() -> Script_Arguments:
    description='Convert time column to UTC'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)

    parser.add_argument(
        '--logday', type=str,
        help = "Day to handle")
    
    parser.add_argument(
        '--logprefix', type=str,
        help = "The prefix used in log file names")

    parser.add_argument(
        '--logdir', type=str,
        help = "The directory the logfiles are stored")
    
    args = parser.parse_args()
    
    return Script_Arguments(
        args.logday,
        args.logprefix,
        args.logdir
    )

async def main( args: Script_Arguments) -> int:
    logger.info(1)
    c1 = await get_columns_from_csv(
        args.logday,
        args.logprefix,
        args.logdir
    )
    logger.info(2)
    logger.info(3)
    c2 = await get_columns_from_csv(
        args.logday,
        args.logprefix,
        args.logdir
    )
    logger.info(4)
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'solar_checker_convert begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_convert end (err={err})')
    sys.exit(err)
