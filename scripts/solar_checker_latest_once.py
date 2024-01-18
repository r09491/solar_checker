#!/usr/bin/env python3

__doc__="""
"""

__version__ = "0.0.0"
__author__ = "r09491@t-online.de"


import os
import sys
import argparse
import asyncio

from datetime import datetime

from aiohttp.client_exceptions import ClientConnectorError

from apsystems import EZ1M
from tasmota import Smartmeter

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def tasmota_latest_get(sm_obj) -> str:
    logger.debug(f'Started "tasmota_latest_get"')

    text =  datetime.now().isoformat('T',"seconds") + ',0,0.000'

    try:
        if await sm_obj.is_power_on():
            logger.debug("Tasmota smarmeter has power.")
            status = await sm_obj.get_status_sns()
            logger.debug("Tasmota smartmeter has output.")
            if status is not None:
                text = f"{status.time},{status.power:.0f},{status.energy:.3f}"

    except ClientConnectorError:
        logger.warning('Cannot connect to smartmeter Tasmota.')

    logger.debug(f'"tasmota_latest_get" done')        
    return text


async def apsystems_latest_get(iv_obj) -> str:
    logger.debug(f'Started "apsystems_latest_get"')

    text = '0,0.000,0.000,0,0.000,0.000'

    try:
        if await iv_obj.is_power_on():
            logger.debug("The APSytems EZ1M inverter has power.")
            output = await iv_obj.get_output_data()
            if output is not None:
                logger.debug("The APSytems EZ1M inverter has output.")
                text = f"{output.p1:.0f},{output.e1:.3f},{output.te1:.3f},"
                text += f"{output.p2:.0f},{output.e2:.3f},{output.te2:.3f}"

    except ClientConnectorError:
        logger.warning('Cannot connect to inverter APSystems EZ1M. Sun?')
    except TypeError:
        logger.error('Unexpected exception TypeError')

    logger.debug(f'"apsystems_latest_get" done')
    return text


async def main(sm_obj, iv_obj) -> int:

    results = await asyncio.gather(
        tasmota_latest_get(sm_obj),
        apsystems_latest_get(iv_obj),
    )
    
    sys.stdout.write(','.join(results) + '\n')

    return 0


def parse_arguments():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from Tasmota Smartmeter and APsystems EZ1M inverter',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--sm_ip', type = str, required = True,
                        help = "IP address of the Tasmota smartmeter")

    parser.add_argument('--sm_port', type = int, default = 80,
                        help = "IP port of the Tasmota Smartmeter")

    parser.add_argument('--iv_ip', type = str, required = True,
                        help = "IP address of the APsystems inverter")

    parser.add_argument('--iv_port', type = int, default = 8050,
                        help = "IP port of the APsystems inverter")
    
    return parser.parse_args()


if __name__ == '__main__':
    logger.info(f'"MAIN" started')
    args = parse_arguments()

    if args.sm_ip is None:
        logger.error('IP address of Tasmota smartmeter is missing.')
        sys.exit(1)

    if args.iv_ip is None:
        logger.error('IP address of APSystem EZ1M inverter is missing.')
        sys.exit(2)

    sm = Smartmeter(args.sm_ip)
    iv = EZ1M(args.iv_ip, args.iv_port)
    err = asyncio.run(main(sm, iv))

    logger.info(f'"MAIN" done {err}')
    sys.exit(err)
