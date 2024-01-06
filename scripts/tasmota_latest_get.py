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

from tasmota import Smartmeter

from aiohttp.client_exceptions import ClientConnectorError

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

async def main(smartmeter):
    if await smartmeter.is_power_on():
        status = await smartmeter.get_status_sns()
        text = f"{status.time},{status.power:.0f},{status.energy:.3f}\n"
        sys.stdout.write(text)
    else:
        sys.stderr.write("TOSMOTA is not on power\n")


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
        asyncio.run(main(sm))
        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to smartmeter.')
        err = 10
    except KeyboardInterrupt: 
        err = 99

    sys.exit(err)
