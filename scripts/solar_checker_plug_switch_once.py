#!/usr/bin/env python3

__doc__="""Tries to make most of the available solar energies in my house.

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

from aiohttp.client_exceptions import ClientConnectorError

import numpy as np

from utils.typing import f64, f64s, t64, t64s, timeslots
from utils.samples import get_columns_from_csv

from poortuya import Smartplug

from dataclasses import dataclass
from typing import Any, Optional


from enum import Enum
class Switch_Status(Enum):
    null = 'Null'
    open = 'Open'
    closed = 'Closed'

    def __str__(self) -> str:
        return self.value


async def tuya_smartplug_switch_set(
        sp: Smartplug,
        ss_desired: Switch_Status) -> Switch_Status:

    logger.info(f'set "{sp.name}" started for "{ss_desired}"')
    is_closed = await (sp.turn_on() if ss_desired.value == "Closed" else sp.turn_off())
    ss_result = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'set "{sp.name}" done with "{ss_result}')        
    return ss_result


async def tuya_smartplug_switch_get(
        sp: Smartplug) -> Switch_Status:

    logger.info(f'get "{sp.name}" started')
    is_closed = await sp.is_switch_closed()
    if is_closed is None: return None    
    ss_result = Switch_Status(
        'Closed' if is_closed else 'Open')
    logger.info(f'get "{sp.name}" done: "{ss_result}"')        
    return ss_result


async def main(
        sp: Smartplug,
) -> int:

    try:
        SPP = {
            'plug1':'SPP1',
            'plug2':'SPP2',
            'plug3':'SPP3',
            'plug0':'SPP4'
        }[sp.name]
    except:
        logger.error(f'Unknown plug name "{sp.name}"')
        return -11

    logger.info(f'Plug sample name  is "{SPP}"')

    
    c = await get_columns_from_csv()
    if c is None:
        logger.error(f'Samples from stdin are not valid')
        return -10

    sbpb = c['SBPB'][-2:]
    sbpb_mean = sbpb.mean()
    logger.info(f'Last SBPB mean "{sbpb_mean:.0f}W"')

    smp = c['SMP'][-2:]
    smp_mean = smp.mean()
    logger.info(f'Last SMP mean "{smp_mean:.0f}W"')
        
    spp =  c[SPP]
    sppon = spp[spp>0]
    sppon_mean = sppon.mean() if sppon.size > 0 else 0.0
    logger.info(f"Plug samples mean is {sppon_mean:.0f}W")

    
    sppon_open = max(0.2*sppon_mean,10)
    logger.info(f"Open power is {sppon_open:.0f}W")
    sppon_closed = max(min(0.8*sppon_mean,100),5) 
    logger.info(f"Closed power is {sppon_closed:.0f}W")
    if sbpb_mean < smp_mean < 0: # Internal to external charge
        logger.info(f"Closed power adapted for charge/import")
        sppon_closed = max(sppon_closed + smp_mean, 5)
        logger.info(f"Adapted closed power is {sppon_closed:.0f}W")

    

    # Switch to be Open if above import average
    is_to_open =  smp_mean > sppon_open
    # Switch to be Closed if below export average
    is_to_closed =  smp_mean < -sppon_closed

    ss_actual = await tuya_smartplug_switch_get(sp)
    if ss_actual is None:
        logger.info(f'"{sp.name}" is not plugged in')
        return 2
    
    logger.info(f'"{sp.name}" currently is "{ss_actual}"')

    # What has to be done now?
    ss_desired = Switch_Status('Open' if is_to_open else
                               'Closed' if is_to_closed else 'Null')
    
    if ((ss_actual == ss_desired) or
        (Switch_Status('Null') == ss_desired)):
        logger.info(f'No action for "{sp.name}"')
        return 1

    
    try:
        ss_result = await tuya_smartplug_switch_set(sp, ss_desired) 
    except ClientConnectorError:
        logger.error('Cannot connect to "{sp.name}".')
        return -11

    # ss_result and ss_desired to be the same 
    logger.info(f'"{sp.name}" became "{ss_result}"')
    return 0


@dataclass
class Script_Arguments:
    plug_name: str

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Switch the plug dependent on power grid export',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    args = parser.parse_args()
    
    return Script_Arguments(args.plug_name)


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'Switching of "{args.plug_name}" started')
    
    err = asyncio.run(main(Smartplug(args.plug_name)))

    logger.info(f'"{args.plug_name}" done (err={err})')
    sys.exit(err)
