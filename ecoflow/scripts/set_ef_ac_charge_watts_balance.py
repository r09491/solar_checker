#!/usr/bin/env python3

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

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
        print(f"New balanced charging rate is {balance}w")
    else:
        print(f"The balance setting timed out")
    return 0


@dataclass
class Script_Arguments:
    grid_watts: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Balnces the charge rate for Nulleinspeisung',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--grid_watts', type = int, required = True,
                        help = "The grid watts as per the smatmeter")

    args = parser.parse_args()
    return Script_Arguments(args.grid_watts)


async def main() -> int:
    args = parse_arguments()

    if args.grid_watts is not None and (args.grid_watts<-800 or
                                        args.grid_watts>+800):
        print(f"Illegal grid watts '{args.grid_watts}'")
        return 1

    err = await process_ac_charge_watts_balance(args.grid_watts)

    return err

if __name__ == '__main__':
    try:
        err = err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
