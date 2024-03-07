#!/usr/bin/env python3

__doc__="""Tries to make most of the available solar energies in my house.

"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"


import os
import sys
import argparse
import asyncio

from aiohttp.client_exceptions import ClientConnectorError

import numpy as np

from typing import Any, Optional
from utils.types import f64, f64s, t64, t64s, timeslots
from utils.samples import get_columns_from_csv

from poortuya import Smartplug

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

from dataclasses import dataclass
from typing import Any, Optional


from enum import Enum
class Switch_Status(Enum):
    null = 'Null'
    open = 'Open'
    closed = 'Closed'

    def __str__(self) -> str:
        return self.value

"""
def str2f64(value: str) -> f64:
    return f64(value)
"""

async def tuya_smartplug_switch_set(sp: Smartplug,
                                    ss_desired: Switch_Status) -> Switch_Status:

    logger.info(f'tuya_smartplug_switch_set started for "{ss_desired}"')
    is_closed = await (sp.turn_on() if ss_desired.value == "Closed" else sp.turn_off())
    ss_result = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'tuya_smartplug_switch_set done with "{ss_result}')        
    return ss_result


async def tuya_smartplug_switch_get(sp: Smartplug) -> Switch_Status:

    logger.info(f'tuya_smartplug_switch_get started')
    is_closed = await sp.is_switch_closed()
    ss_result = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'tuya_smartplug_switch_get done with "{ss_result}"')        
    return ss_result


async def main(sp: Smartplug,
               power_mean_import_open: f64,
               power_mean_export_closed: f64,
               power_mean_deviation: f64,
               power_samples: int, f: Any) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.info(f'Samples from stdin are not valid')
        return 10

    smp = c['SMP']
    if smp.size != power_samples:
        logger.error(f'Wrong number of smartmeter records "{smp.size}"')
        return 11
    smp_mean, smp_std = smp.mean(), smp.std()
    logger.info(f'Last smartmeter means "{smp_mean:.0f}W", std "{smp_std:.0f}W"')

    name = sp.name
    spp = c['SPP1'] if name == 'plug1' else \
        c['SPP2'] if name == 'plug2' else \
        c['SPP3'] if name == 'plug3' else \
        c['SPP4'] if name == 'plug4' else None
    if spp is None or spp.size != power_samples:
        logger.error(f'Wrong number of plug records "{spp.size}" for "{name}"')
        return 12
    
    spp_mean, spp_std = spp.mean(), spp.std()
    logger.info(f'Last "{sp.name}" smartplug means "{spp_mean:.0f}W", std "{spp_std:.0f}W"')
        

    # Switch to be Open if below average and standard deviation
    is_to_open =  smp_mean > power_mean_import_open
    # Switch to be Closed if above average and standard deviation
    is_to_closed =  smp_mean < -power_mean_export_closed and smp_std < power_mean_deviation

    ss_actual = await tuya_smartplug_switch_get(sp)
    logger.info(f'The smartplug switch currently is "{ss_actual}"')

    # What has to be done now?
    ss_desired = Switch_Status('Open' if is_to_open else
                               'Closed' if is_to_closed else 'Null')
    logger.info(f'The smartplug switch goal is "{ss_desired}"')

    if ss_desired == Switch_Status('Null'):
        logger.warning(f'Net mean "{smp_mean:.0f}" or std "{smp_std:.0f}" do not match.')
        logger.info(f'The smartplug switch "{name}" remains "{ss_actual}"')
    
    elif ss_actual != ss_desired:
        logger.info(f'The smartplug "{name}" is desired to "{ss_desired}"')
        try:
            ss_result = await tuya_smartplug_switch_set(sp, ss_desired) 
        except ClientConnectorError:
            logger.error('Cannot connect to smartplug "{name}".')
            return 1
        # ss_result and ss_desired to be the same 
        logger.info(f'The smartplug switch "{name}" became "{ss_result}"')
            
    else:
        logger.info(f'The smartplug switch "{name}" remains "{ss_actual}"')

    return 0


@dataclass
class Script_Arguments:
    plug_name: str
    power_mean_import_open: f64
    power_mean_export_closed: f64
    power_mean_deviation: f64
    power_samples: int
    
def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power switch parameters',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    parser.add_argument('--power_mean_import_open', type = f64, default = 20.0,
                        help = "Net power to open the plug")

    parser.add_argument('--power_mean_export_closed', type = f64, default = 20.0,
                        help = "Net power to close the plug")

    parser.add_argument('--power_mean_deviation', type = f64, default = 10.0,
                        help = "Maximum deviation of the samples")

    parser.add_argument('--power_samples', type = int, default = 10,
                        help = "Number of recorded samples to use")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.plug_name,
                            args.power_mean_import_open,
                            args.power_mean_export_closed,
                            args.power_mean_deviation,
                            args.power_samples)


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'Switching of "{args.plug_name}" started')
    
    if args.power_mean_import_open < 0:
        logger.error(f'Provided mean open "{args.power_mean_import_open}" must not be negative')
        logger.error(f'Switching of "{args.plug_name}" aborted (err=1)')
        sys.exit(1)

    if args.power_mean_export_closed < 0:
        logger.error(f'Provided mean closed "{args.power_mean_export_closed}" must not be negative')
        logger.error(f'Switching of "{args.plug_name}" aborted (err=2)')
        sys.exit(2)

    max_deviation = (args.power_mean_import_open + args.power_mean_export_closed) * 0.50
    if args.power_mean_deviation > max_deviation:
        logger.error(f'Provided deviation "{args.power_mean_deviation}" larger than max "{max_deviation:.0f}"')
        logger.error(f'Switching of "{args.plug_name}" aborted (err=4)')
        sys.exit(4)
        
    err = asyncio.run(main(Smartplug(args.plug_name),
                           args.power_mean_import_open,
                           args.power_mean_export_closed,
                           args.power_mean_deviation,
                           args.power_samples,
                           sys.stdin))

    logger.info(f'Switching of "{args.plug_name}" done (err={err})')
    sys.exit(err)
