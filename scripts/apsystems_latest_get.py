#!/usr/bin/env python3

__doc__="""
Writes the latest inverter data to stdout
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

from apsystems import Inverter

from aiohttp.client_exceptions import ClientConnectorError

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(inverter) -> int:
    text = '0,0.000,0.000,0,0.000,0.000'

    try:
        if await inverter.is_power_on():
            logger.debug("The APsystems inverter is powered.")
            output = await inverter.get_output_data()
            if output is not None:
                logger.debug("The APsystems inverter provides output.")
                text = f"{output.p1:.0f},{output.e1:.3f},{output.te1:.3f},"
                text += f"{output.p2:.0f},{output.e2:.3f},{output.te2:.3f}"

        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to inverter.')
        err = 10
    except TypeError:
        logger.error('Unexpected exception TypeError')
        err = 11

    # To keep synchronous output is always required            
    sys.stdout.write(text + '\n')

    return err


def parse_arguments():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from APsystems EZ1M inverter',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--ip', type = str,
                        help = "IP address of the APsystems inverter")

    parser.add_argument('--port', type = int, default = 8050,
                        help = "IP port of the APsystems inverter")
    
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    if args.ip is None:
        logger.error('IP address is missing.')
        sys.exit(1)

    iv = Inverter(args.ip, args.port)

    try:
        err = asyncio.run(main(iv))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
