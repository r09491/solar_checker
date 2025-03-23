#!/usr/bin/env python3

__doc__="""
"""

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

from datetime import datetime

#from aiohttp.client_exceptions import ClientConnectorError

#from typing import Optional

from ecoflow import (
    Delta_Max,
    WATTS,
    WATTS_XT60
)
    

##from dataclasses import dataclass


async def dm_latest_get(dm: Delta_Max) -> str:
    logger.info(f'dm_latest_get started')
 
    try:
        watts = await dm.get_watts()
    except:
        watts = None
    
    if watts is not None:
        logger.info('Delta Max has data')
        text = ','.join(str(w) for w in watts.values())
    else:
        logger.error('No data from Delta Max')
        text = ','.join('0' for w in range(len(WATTS+WATTS_XT60)))

    logger.info(f'dm_latest_get done')        
    return text


async def main(dm: Delta_Max) -> int:

    nowiso = datetime.now().isoformat('T',"seconds")

    # The order in the list determines the columns in the recording
    # file
    
    results = await asyncio.gather(
        dm_latest_get(dm)
    )

    sys.stdout.write(nowiso + ',' + ','.join(results) + '\n')
    sys.stdout.flush()
    
    return 0

    
def parse_arguments() -> None:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        description='Get the latest power values from the Delta Max',
        prog=os.path.basename(sys.argv[0]),
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)
    parser.parse_args()
    return None

if __name__ == '__main__':
    parse_arguments()
    
    logger.info(f'Delta Max recording latest started')
    err = asyncio.run(main(dm = Delta_Max()))
    logger.info(f'Delta Max recording latest done (err={err})')

    sys.exit(err)
