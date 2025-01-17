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

async def process_beep_muted(muted: int = None) -> int:

    dm = Delta_Max()
    
    m = await dm.get_beep_muted()
    print(f"Old beep state is {'MUTED' if m else 'NORMAL'}")

    if muted is None:
        return 0
    
    await dm.set_beep_muted(muted)
    
    for i in range(3):
        await asyncio.sleep(2)
        m = await dm.get_beep_muted()
        if m == muted:
            break

    print(f"New beep state is {'MUTED' if m else 'NORMAL'}")

    return 0


@dataclass
class Script_Arguments:
    muted: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Enable/Diable USB output',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--muted', type = int, default = None,
                        help = "The mute flag for the beep")

    args = parser.parse_args()
    return Script_Arguments(args.muted)


async def main() -> int:
    args = parse_arguments()

    if args.muted is not None and args.muted not in [0,1]:
        print(f"Illegal muted state '{args.muted}'")
        return 1

    err = await process_beep_muted(args.muted)

    return err

if __name__ == '__main__':
    try:
        err = err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
