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

async def process_watts() -> int:
    
    dm = Delta_Max()    
    w = await dm.get_watts()
    logger.info(f"Delta Max [sumin, sumout, usb1, usb2, qc1, qc2, pd1, pd2, acin, acout, xt60] is {w} watts")

    return 0


async def main() -> int:        

    err = await process_watts()    
    return err


if __name__ == '__main__':
    try:
        err = asyncio.run(main())
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
