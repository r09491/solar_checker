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

async def process_ac_charge_watts_balance(smp: int, minp: int, maxp:int) -> int:

    dm = Delta_Max()
    
    balance = await dm.set_ac_charge_watts_balance(smp, minp, maxp)
    if balance is not None: 
        logger.info(f"Balance charging rate is {balance}w")
        return 0
    else:
        logger.info(f"Balance charging rate not modified")
        return 1


@dataclass
class Script_Arguments:
    grid_watts: int
    min_grid_watts: int
    max_grid_watts: int
    min_charge_watts: int
    max_charge_watts: int

MIN_GRID_WATTS = -200
MAX_GRID_WATTS = 200
MIN_CHARGE_WATTS = 100
MAX_CHARGE_WATTS = 400
    
def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Balnces the charge rate for Nulleinspeisung',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--grid_watts', type = int, default = None,
                        help = "The grid watts as per the smartmeter")

    parser.add_argument('--min_grid_watts', type = int, default = MIN_GRID_WATTS,
                        help = "Minimum grid watts for balance")

    parser.add_argument('--max_grid_watts', type = int, default = MAX_GRID_WATTS,
                        help = "Maximum grid_watts for balance")
    
    parser.add_argument('--min_charge_watts', type = int, default = MIN_CHARGE_WATTS,
                        help = "Minimum charge watts for balance")

    parser.add_argument('--max_charge_watts', type = int, default = MAX_CHARGE_WATTS,
                        help = "Maximum charge_watts for balance")

    args = parser.parse_args()
    return Script_Arguments(args.grid_watts,
                            args.min_grid_watts,
                            args.max_grid_watts,
                            args.min_charge_watts,
                            args.max_charge_watts)



async def main() -> int:
    args = parse_arguments()

    gw = args.grid_watts
    if gw is not None:
        gw = max(min(gw, args.max_grid_watts),args.min_grid_watts)

    if not (MIN_CHARGE_WATTS <= args.min_charge_watts < args.max_charge_watts):
        logger.error(f'Min charge watts out of range')
        return -1

    if not (MAX_CHARGE_WATTS >= args.max_charge_watts > args.min_charge_watts):
        logger.error(f'Max charge watts out of range')
        return -2
        
    err = await process_ac_charge_watts_balance(gw,args.min_charge_watts,args.max_charge_watts)

    return err

if __name__ == '__main__':
    try:
        err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'Done with (err={err}).')
    sys.exit(err)
