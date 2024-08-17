#!/usr/bin/env python3

__doc__="""Gets the latest data from an Tasmota smartmeter, an
APsystems inverter, a Tuya smartplug, an Anker solarbank and writes
them to stdout in a comma separated row. This script is designed to be
called by cron.
"""

__version__ = "0.0.3"
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

    try:
        pdata = await sb.get_power_data()
    except:
        pdata = None
    if pdata is not None:
        logger.debug("Anker solarbank provides data.")
        text = f'{pdata.input_power:.0f}'
        text += f',{pdata.output_power:.0f}'
        text += f',{pdata.battery_power:.0f}'
        text += f',{pdata.battery_soc:.2f}'
    else:
        logger.error("Anker solarbank provides no data (?Server down).")
        
    logger.info(f'anker_solarbank_latest_get done')        
    return text


async def tuya_smartplug_latest_get(sp: Smartplug) -> str:
    logger.info(f'tuya_smartplug_latest_get started')
    text = '0'

    if sp is None:
        logger.warning('A Tuya smartplug is "UNUSED".')
        await asyncio.sleep(1)

    else:
        status = await sp.get_status()
        if status is not None:
            logger.info(f'Tuya smartplug "{sp.name}" is "ON".')
            text = f'{status.power:.0f}'

        else:
            logger.warning(f'Tuya smartplug "{sp.name}" is "OFF".')
    
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
        for trial in range(3):
            if await iv.is_power_on():
                logger.info('The APSytems EZ1M is "ON".')

                output = await iv.get_output_data()
                if output is not None:
                    logger.info('The APSytems EZ1M inverter has data.')
                    text = f'{output.p1:.0f},{output.e1:.3f},{output.te1:.3f}'
                    text += f',{output.p2:.0f},{output.e2:.3f},{output.te2:.3f}'
                    break                    

                logger.warning('The APSytems EZ1M has no data')

            logger.warning('The APSytems EZ1M is "OFF". Sun? Local?')
            await asyncio.sleep(2)
            
    except ClientConnectorError:
        logger.warning('Cannot connect to inverter APSystems EZ1M. Sun?')
    except TypeError:
        logger.error('Unexpected exception TypeError')
    #except:
    #    logger.error('Unknown error')
        
    logger.info(f'apsystems_inverter_latest_get done')
    return text


async def main(sm: Smartmeter, iv: Inverter,
               sph: Smartplug, sb: Solarbank,
               sp1: Smartplug, sp2: Smartplug,
               sp3: Smartplug, sp4: Smartplug) -> int:

    # Tasmota sometimes returns with an invalid time. Ensure there is
    # a valid time!
    nowiso = datetime.now().isoformat('T',"seconds")

    # The order in the list determines the columns in the recording
    # file
    
    results = await asyncio.gather(
        tasmota_smartmeter_latest_get(sm),
        apsystems_inverter_latest_get(iv),
        tuya_smartplug_latest_get(sph),
        anker_solarbank_latest_get(sb),
        tuya_smartplug_latest_get(sp1),
        tuya_smartplug_latest_get(sp2),
        tuya_smartplug_latest_get(sp3),
        tuya_smartplug_latest_get(sp4),
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
    sp_balcony: str
    sp_switch_1: str
    sp_switch_2: str
    sp_switch_3: str
    sp_switch_4: str
    
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

    parser.add_argument('--sp_balcony', type = str, default = None,
                        help = "Name of the plug at the house plug")

    parser.add_argument('--sp_switch_1', type = str, default = None,
                        help = "Name of the plug used as switch 1")

    parser.add_argument('--sp_switch_2', type = str, default = None,
                        help = "Name of the plug used as switch 2")

    parser.add_argument('--sp_switch_3', type = str, default = None,
                        help = "Name of the plug used as switch 3")

    parser.add_argument('--sp_switch_4', type = str, default = None,
                        help = "Name of the plug used as switch 4")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.sm_ip, args.sm_port,
                            args.iv_ip, args.iv_port,
                            args.sp_balcony,
                            args.sp_switch_1, args.sp_switch_2,
                            args.sp_switch_3, args.sp_switch_4)


if __name__ == '__main__':
    logger.info(f'Recording latest started')
    args = parse_arguments()

    if args.sm_ip is None:
        logger.error('IP address of Tasmota smartmeter is missing.')
        sys.exit(1)

    if args.iv_ip is None:
        logger.error('IP address of APSystem EZ1M inverter is missing.')
        sys.exit(2)

    if args.sp_balcony is not None and \
       args.sp_switch_1 is not None and \
       args.sp_balcony == args.sp_switch_1 :
        logger.error('Illegal usage of smartplug 1.')
        sys.exit(3)

    if args.sp_balcony is not None and \
       args.sp_switch_2 is not None and \
       args.sp_balcony == args.sp_switch_2 :
        logger.error('Illegal usage of smartplug 2.')
        sys.exit(4)

    if args.sp_balcony is not None and \
       args.sp_switch_3 is not None and \
       args.sp_balcony == args.sp_switch_3 :
        logger.error('Illegal usage of smartplug 3.')
        sys.exit(5)

    if args.sp_balcony is not None and \
       args.sp_switch_4 is not None and \
       args.sp_balcony == args.sp_switch_4 :
        logger.error('Illegal usage of smartplug 4.')
        sys.exit(5)

    sb = Solarbank()        
    sm = Smartmeter(args.sm_ip)
    iv = Inverter(args.iv_ip, args.iv_port)
    sph = Smartplug(args.sp_balcony) if args.sp_balcony is not None else None
    sp1 = Smartplug(args.sp_switch_1) if args.sp_switch_1 is not None else None
    sp2 = Smartplug(args.sp_switch_2) if args.sp_switch_2 is not None else None
    sp3 = Smartplug(args.sp_switch_3) if args.sp_switch_3 is not None else None
    sp4 = Smartplug(args.sp_switch_4) if args.sp_switch_4 is not None else None
    err = asyncio.run(main(sm, iv, sph, sb, sp1, sp2, sp3, sp4))

    logger.info(f'Recording latest done (err={err})')
    sys.exit(err)
