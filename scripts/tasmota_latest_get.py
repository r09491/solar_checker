#!/usr/bin/env python3

__doc__="""
Writes the latest smartmeter data to stdout
"""

__version__ = "0.0.0"
__author__ = "r09491@t-online.de"

import os
import sys
import argparse
import asyncio

from datetime import datetime

from tasmota import Smartmeter

from aiohttp.client_exceptions import ClientConnectorError

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(smartmeter) -> int:
    """ The text has to be preset in the case of an error """
    text =  datetime.now().isoformat('T',"seconds") + ',0,0.000'

    try:
        if await smartmeter.is_power_on():
            status = await smartmeter.get_status_sns()
            if status is not None:
                """ Override the preset """
                text = f"{status.time},{status.power:.0f},{status.energy:.3f}"

        err = 0
    except ClientConnectorError:
        logger.warning('Cannot connect to smartmeter.')
        err = 10

    """ There is always output required """
    sys.stdout.write(text + '\n')

    return err

    
def parse_arguments():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from Tasmota',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--ip', type = str,
                        help = "IP address of the Tasmota sensor")

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    if args.ip is None:
        logger.error('IP address is missing.')
        sys.exit(1)

    sm = Smartmeter(args.ip)

    try:
        err = asyncio.run(main(sm))
    except KeyboardInterrupt: 
        err = 99

    sys.exit(err)
