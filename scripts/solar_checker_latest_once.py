#!/usr/bin/env python3

__doc__="""Gets the latest data from an Tasmota smartmeter, an
APsystems inverter, a Tuya smartplug, a Anker solarbank and writes
them to stdout in a comma separated row. This script is designed to be
called by cron.
"""

__version__ = "0.0.2"
__author__ = "r09491@gmail.com"


import os
import sys
import argparse
import asyncio

from datetime import datetime

from aiohttp.client_exceptions import ClientConnectorError

from apsystems import Inverter
from tasmota import Smartmeter
from poortuya import Smartplug
from pooranker import Solarbank

from dataclasses import dataclass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(__name__))


async def anker_solarbank_latest_get(sb: Solarbank) -> str:
    logger.info(f'anker_solarbank_latest_get started')
    text = '0.000,0.000,0.000,0.00'

    pdata = await sb.get_power_data()
    if pdata is not None:
        logger.debug("Anker solarbank has data.")
        text = f'{pdata.input_power:.0f}'
        text += f',{pdata.output_power:.0f}'
        text += f',{pdata.battery_power:.0f}'
        text += f',{pdata.battery_soc:.2f}'

    logger.info(f'anker_solarbank_latest_get done')        
    return text


async def tuya_smartplug_latest_get(sp: Smartplug) -> str:
    logger.info(f'tuya_smartplug_latest_get started')
    text = '0'

    status = await sp.get_status()
    if status is not None:
        logger.debug("Tuya smartplug has data.")
        text = f'{status.power:.0f}'

    logger.info(f'tuya_smartplug_latest_get done')        
    return text


async def tasmota_smartmeter_latest_get(sm: Smartmeter) -> str:
    logger.info(f'tasmota_smartmeter_latest_get started')
    
    text = '0,0.000'

    try:
        if await sm.is_power_on():
            logger.debug('Tasmota smarmeter is "ON".')

            status = await sm.get_status_sns()
            logger.debug("Tasmota smartmeter has data.")
            if status is not None:
                # Sometimes there is an invalid time. Do not use the
                # one of status!
                text = f'{status.power:.0f},{status.energy:.3f}'

        else:
            logger.warning('The Tasmota Smartmeter is "OFF".')

    except ClientConnectorError:
        logger.warning('Cannot connect to smartmeter Tasmota.')

    logger.info(f'tasmota_smartmeter_latest_get done')        
    return text


async def apsystems_inverter_latest_get(iv: Inverter) -> str:
    logger.info(f'apsystems_inverter_latest_get started')

    text = '0,0.000,0.000,0,0.000,0.000'

    try:
        if await iv.is_power_on():
            logger.debug('The APSytems EZ1M is "ON".')

            output = await iv.get_output_data()
            if output is not None:
                logger.debug('The APSytems EZ1M inverter has data.')
                text = f'{output.p1:.0f},{output.e1:.3f},{output.te1:.3f}'
                text += f',{output.p2:.0f},{output.e2:.3f},{output.te2:.3f}'

        else:
            logger.warning('The APSytems EZ1M is "OFF". Sun? Local?')
            
    except ClientConnectorError:
        logger.warning('Cannot connect to inverter APSystems EZ1M. Sun?')
    except TypeError:
        logger.error('Unexpected exception TypeError')

    logger.info(f'apsystems_inverter_latest_get done')
    return text


async def main(sm: Smartmeter, iv: Inverter, sp: Smartplug, sb: Solarbank) -> int:

    # Tasmota sometimes returns with an invalid time. Ensure there is
    # a valid time!
    nowiso = datetime.now().isoformat('T',"seconds")

    results = await asyncio.gather(
        tasmota_smartmeter_latest_get(sm),
        apsystems_inverter_latest_get(iv),
        tuya_smartplug_latest_get(sp),
        anker_solarbank_latest_get(sb),
    )

    sys.stdout.write(nowiso + ',' + ','.join(results) + '\n')
    sys.stdout.flush()
    
    return 0


@dataclass
class Script_Arguments:
    sm_ip: str
    sm_port: int
    iv_ip: str
    iv_port: int
    sp_name: str
    sb_sn:str
    
def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from various systems',
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

    parser.add_argument('--sp_name', type = str, required = True,
                        help = "Name of the plug in the config file")

    parser.add_argument('--sb_sn', type = str, required = True,
                        help = "Serial number of the solarbank")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.sm_ip, args.sm_port,
                            args.iv_ip, args.iv_port,
                            args.sp_name, args.sb_sn)


if __name__ == '__main__':
    logger.info(f'Recording latest started')
    args = parse_arguments()

    if args.sm_ip is None:
        logger.error('IP address of Tasmota smartmeter is missing.')
        sys.exit(1)

    if args.iv_ip is None:
        logger.error('IP address of APSystem EZ1M inverter is missing.')
        sys.exit(2)

    sm = Smartmeter(args.sm_ip)
    iv = Inverter(args.iv_ip, args.iv_port)
    sp = Smartplug(args.sp_name)
    sb = Solarbank(args.sb_sn)
    err = asyncio.run(main(sm, iv, sp, sb))

    logger.info(f'Recording latest done (err={err})')
    sys.exit(err)
