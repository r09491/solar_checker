#!/usr/bin/env python3

__doc__="""Sets the power output (home load) of the anker solarbank to
a value from 100W to 800W. It is not guaranteed the solarbank will
obey."""

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
import argparse
import asyncio

from pooranker import Solarbank

from dataclasses import dataclass


async def anker_home_load_set(home_load: int) -> bool:
    try:
        is_done = await Solarbank().set_home_load(home_load)
    except:
        is_done = False
    return is_done


async def main(home_load: int) -> int:
    
    logger.info(f'Going for home load goal "{home_load:.0f}"')
    is_done = await anker_home_load_set(home_load)
    logger.info(f"Achieved home load goal is {'set' if is_done else 'kept'}")

    return 0 if is_done else 1


@dataclass
class Script_Arguments:
    load: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=__name__, 
        description='Set the home load of the solarbank',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--load', type = int, default = 100,
                        help = "Value of home load to be set")
    
    
    args = parser.parse_args()

    return Script_Arguments(args.load)


if __name__ == '__main__':
    args = parse_arguments()

    if args.load < 0:
        logger.error(f'home load "{args.load}" too low (err=-1)')
        sys.exit(-1)
        
    if args.load > 999:
        logger.error(f'home load "{args.load}" too high (err=-2)')
        sys.exit(-2)

    try:
        err = asyncio.run(main(args.load))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'done with (err={err}).')
    sys.exit(err)
