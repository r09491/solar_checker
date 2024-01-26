#!/usr/bin/env python3

__doc__="""
Writes the latest tuya smartmeter data to stdout
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

from poortuya import Smartplug

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def tuya_smartplug_latest_get(sp: Smartplug) -> str:
    logger.info(f'tuya_smartplug_latest_get started')
    text = '0,0,0'

    status = await sp.get_status()
    if status is not None:
        logger.info("Tuya smartplug has data I[mA],U[V],P[W]")
        text = f'{status.current:.0f},{status.voltage:.0f},{status.power:.0f}'

    logger.info(f'tuya_smartplug_latest_get done')        
    return text


async def main(sp: Smartplug) -> int:
    text = '0,0,0'

    try:
        text = await tuya_smartplug_latest_get(sp) 
        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to smartplug.')
        err = 10

    # To keep synchronous output is always required            
    sys.stdout.write(text + '\n')
    sys.stdout.flush()
    
    return err


@dataclass
class Script_Arguments:
    plug_name: str

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from the Tuya smartplug',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    args = parser.parse_args()

    return Script_Arguments(args.plug_name)


if __name__ == '__main__':
    args = parse_arguments()

    if args.plug_name is None:
        logger.error('Plug name of smartplug is  missing.')
        sys.exit(1)

    try:
        sp = Smartplug(args.plug_name)
    except KeyError:
        logger.error('Plug name is not in the config file ".poortuya"')
        sys.exit(2)

    try:
        err = asyncio.run(main(sp))
    except KeyboardInterrupt: 
        err = 0
       
    sys.exit(err)
