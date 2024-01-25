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

from enum import Enum
class Switch_Status(Enum):
    open = 'Open'
    closed = 'Closed'

    def __str__(self) -> str:
        return self.value

async def tuya_smartplug_switch_set(sp: Smartplug, ss: Switch_Status) -> int:
    logger.info(f'tuya_smartplug_switch_set started')
    closed = await sp.turn_on() if ss.value == "Closed" else await sp.turn_off()
    logger.info(f'tuya_smartplug_switch_set {"Closed" if closed else "Open"} done')        
    return 0

async def main(sp: Smartplug, ss: Switch_Status) -> int:

    try:
        await tuya_smartplug_switch_set(sp,ss) 
        err = 0
    except ClientConnectorError:
        logger.error('Cannot connect to smartplug.')
        err = 10

    return err


@dataclass
class Script_Arguments:
    plug_name: str
    switch_state: Switch_Status

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Open or closes the Tuya smartplug switch',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    parser.add_argument('--switch_state', type = Switch_Status,
                        choices=list(Switch_Status), required = True,
                        help = "New state of the Tuya smartplug switch")

    args = parser.parse_args()

    return Script_Arguments(args.plug_name, args.switch_state)


if __name__ == '__main__':
    args = parse_arguments()

    if args.plug_name is None:
        logger.error('Name of smartplug is  missing.')
        sys.exit(1)

    if args.switch_state is None:
        logger.error('State of smartplug switch is  missing.')
        sys.exit(2)

    try:
        sp = Smartplug(args.plug_name)
    except KeyError:
        logger.error('Plug name is not in the config file ".poortuya"')
        sys.exit(2)

    try:
        err = asyncio.run(main(sp, args.switch_state))
    except KeyboardInterrupt: 
        err = 0
       
    sys.exit(err)
