#!/usr/bin/env python3

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
import asyncio

import argparse
import json

from dataclasses import dataclass

from ecoflow import Delta_Max

async def process_ac_charge_watts_balance(smp: int) -> int:

    dm = Delta_Max()
    
    balance = await dm.set_ac_charge_watts_balance(smp)
    if balance is not None: 
        logger.info(f"Balance charging rate is {balance}w")
        return 0
    else:
        logger.info(f"Balance charging rate not modified")
        return 1


@dataclass
class Script_Arguments:
    grid_watts: int
    min_watts: int
    max_watts: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Balnces the charge rate for Nulleinspeisung',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--grid_watts', type = int, default = None,
                        help = "The grid watts as per the smartmeter")

    parser.add_argument('--min_watts', type = int, default = -800,
                        help = "Minimum watts for balance")

    parser.add_argument('--max_watts', type = int, default = 800,
                        help = "Maximum watts for balance")
    
    args = parser.parse_args()
    return Script_Arguments(args.grid_watts,args.min_watts,args.max_watts)


async def main() -> int:
    args = parse_arguments()

    gw = args.grid_watts
    if gw is not None:
        gw = max(min(gw, args.max_watts),args.min_watts)

    err = await process_ac_charge_watts_balance(gw)

    return err

if __name__ == '__main__':
    try:
        err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'Done with (err={err}).')
    sys.exit(err)
