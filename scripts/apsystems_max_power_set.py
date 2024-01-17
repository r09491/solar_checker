#!/usr/bin/env python3

__doc__="""
Sets the new power limit to the APsystems EZ1 inverter
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


async def main(inverter, new_max_power) -> int:
    err = 0
    
    max_power = await inverter.get_max_power()
    if max_power is None:
        logger.error(f"Could not get max power limit")
        return 10
        
    logger.info(f"Current Max Power Limit: {max_power}W")

    if new_max_power is None:
        return 0
    
    # Set maximum power limit (ensure the value is within valid range)
    set_max_power_response = await inverter.set_max_power(new_max_power)
    if set_max_power_response is None:
        logger.error(f"Could not set max power limit")
        return 11
        
    logger.info(f"Commanded Power: {set_max_power_response}W")

    max_power = await inverter.get_max_power()
    if max_power is None:
        logger.error(f"Could not get max power limit")
        return 12
    
    logger.info(f"New Max Power Limit: {max_power}W")
                
    # Set power status (ensure "ON" or other value is valid)
    set_power_status_response = await inverter.set_device_power_status("ON")
    if set_power_status_response is None:
        logger.error(f"Could not get power status")
        return 13
        
    logger.info(f"Commanded Power Status: {'ON' if set_power_status_response == 0 else 'OFF'}")

    # Get current power status
    power_status = await inverter.get_device_power_status()
    if power_status is None:
        logger.error(f"Could not get device power status")
        return 14
            
    logger.info(f"New Power Status: {'ON' if power_status == 0 else 'OFF'}")

    return err


def parse_arguments():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Set the the maximum power of the inverter',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--ip', type = str,
                        help = "IP address of the APsystems inverter")

    parser.add_argument('--port', type = int, default = 8050,
                        help = "IP port of the APsystems inverter")
    
    parser.add_argument('--max_power', type = int,
                        help = "The new maximum power of the inverter")
    
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    if args.ip is None:
        logger.error('IP address is missing.')
        sys.exit(1)

    if args.max_power is not None and (args.max_power < 30 or
                                       args.max_power > 800):
        logger.error(f'Input "{args.max_power}" is out of legal range.')
        sys.exit(2)

    if args.max_power is not None and args.max_power > 600:
        logger.info(f'The power limit for inverters in Germany is 600W.')
        logger.info(f'Be advised to consult your lawyer!')
        
    ez1m = EZ1M(args.ip, args.port)

    try:
        err = asyncio.run(main(ez1m, args.max_power))
    except ClientConnectorError:
        logger.error('Cannot connect to inverter.')
        err = 10
    except KeyboardInterrupt: 
        err = 99

    sys.exit(err)
