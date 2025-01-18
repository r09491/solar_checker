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

async def process_ac_charge_watts(watts: int = None) -> int:

    dm = Delta_Max()
    
    w = await dm.get_ac_charge_watts()
    logger.info(f"Old charging rate is {w}w")

    if watts is None:
        return 0
    
    await dm.set_ac_charge_watts(watts)
    
    for i in range(3):
        await asyncio.sleep(2)
        w = await dm.get_ac_charge_watts()
        if w == watts:
            break

    logger.info(f"New charging rate is {w}w")
    
    return 0


@dataclass
class Script_Arguments:
    watts: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Set the AC charging rate',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--watts', type = int, default = None,
                        help = "The AC charging rate in watts")

    args = parser.parse_args()
    return Script_Arguments(args.watts)


async def main() -> int:
    args = parse_arguments()

    if args.watts is not None and 100>args.watts>800:
        logger.info(f"Illegal charging rate '{args.watts}'")
        return 1

    err = await process_ac_charge_watts(args.watts)

    return err

if __name__ == '__main__':
    try:
        err = err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
