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

from typing import Optional
from dataclasses import dataclass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

from enum import Enum
class Switch_Status(Enum):
    open = 'Open'
    closed = 'Closed'

    def __str__(self) -> str:
        return self.value

async def tuya_smartplug_switch_set(sp: Smartplug, ss_command: Switch_Status) -> Switch_Status:
    logger.info(f'tuya_smartplug_switch_set started')
    is_closed = await (sp.turn_on() if ss_command.value == "Closed" else sp.turn_off())
    logger.info(f'tuya_smartplug_switch_set done')        
    ss_result = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'The switch status is "{ss_result}".')
    return ss_result

async def tuya_smartplug_switch_get(sp: Smartplug) -> Switch_Status:
    logger.info(f'tuya_smartplug_switch_get started')
    is_closed = await sp.is_switch_closed()
    logger.info(f'tuya_smartplug_switch_get done')
    ss = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'The switch status is "{ss}".')
    return ss

async def main(sp: Smartplug, ss: Switch_Status) -> Optional[Switch_Status]:
    if ss is None:
        # Query the switch state
        try:
            switch_status = await tuya_smartplug_switch_get(sp) 
        except ClientConnectorError:
            logger.error('Cannot connect to smartplug.')
            return None

    else:
        # Set the switch state
        try:
            switch_status = await tuya_smartplug_switch_set(sp,ss) 
        except ClientConnectorError:
            logger.error('Cannot connect to smartplug.')
            return None

    return switch_status


@dataclass
class Script_Arguments:
    plug_name: str
    switch_status: Switch_Status

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Open or closes the Tuya smartplug switch',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    parser.add_argument('--switch_status', type = Switch_Status,
                        choices=list(Switch_Status), default = None,
                        help = "New state of the Tuya smartplug switch")

    args = parser.parse_args()

    return Script_Arguments(args.plug_name, args.switch_status)


if __name__ == '__main__':
    args = parse_arguments()

    if args.plug_name is None:
        logger.error('Name of smartplug is  missing.')
        sys.exit(1)

    try:
        sp = Smartplug(args.plug_name)
    except KeyError:
        logger.error('Plug name is not in the config file ".poortuya"')
        sys.exit(2)

    try:
        switch_status = asyncio.run(main(sp, args.switch_status))
        sys.stdout.write(str(switch_status) + '\n')
    except KeyboardInterrupt: 
        pass
       
    sys.exit(0)
