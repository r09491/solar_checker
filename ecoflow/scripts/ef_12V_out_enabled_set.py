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

async def process_12V_out_enabled(enabled: int = None) -> int:

    dm = Delta_Max()
    
    e = await dm.get_12V_out_enabled()
    logger.info(f"Old 12V out state is {'ON' if e else 'OFF'}")

    if enabled is None:
        return 0
    
    await dm.set_12V_out_enabled(enabled)
    
    for i in range(3):
        await asyncio.sleep(2)
        e = await dm.get_12V_out_enabled()
        if e == enabled:
            break

    logger.info(f"New 12V out state is {'ON' if e else 'OFF'}")

    return 0


@dataclass
class Script_Arguments:
    enabled: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Enable/Diable 12V output',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--enabled', type = int, default = None,
                        help = "The enable flag for the 12V output")

    args = parser.parse_args()
    return Script_Arguments(args.enabled)


async def main() -> int:
    args = parse_arguments()

    if args.enabled is not None and args.enabled not in [0,1]:
        logger.info(f"Illegal enabled state '{args.enabled}'")
        return 1

    err = await process_12V_out_enabled(args.enabled)

    return err

if __name__ == '__main__':
    try:
        err = err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
