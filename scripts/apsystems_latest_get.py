#!/usr/bin/env python3

__doc__="""
Writes the latest inverter data to stdout
"""

__version__ = "0.0.0"
__author__ = "r09491@t-online.de"

import os
import sys
import argparse
import asyncio

from apsystems import EZ1M

from aiohttp.client_exceptions import ClientConnectorError

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def main(inverter):
    text = 5*','

    if await inverter.is_power_on():
        output = await inverter.get_output_data()
        if output is not None:
            text = f"{output.p1:.0f},{output.e1:.3f},{output.te1:.3f},"
            text += f"{output.p2:.0f},{output.e2:.3f},{output.te2:.3f}"

    # To keep synchron output is always required            
    sys.stdout.write(text + '\n')


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

    ez1m = EZ1M(args.ip, args.port)

    try:
        asyncio.run(main(ez1m))
        err = 0
    except ClientConnectorError:
        """To be kept in sync with smartmeter output"""
        sys.stdout.write(5*','+ '\n')
        logger.warning('Cannot connect to inverter.')
        err = 10
    except KeyboardInterrupt: 
        err = 99

    sys.exit(err)
