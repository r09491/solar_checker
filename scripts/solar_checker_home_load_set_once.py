#!/usr/bin/env python3

__doc__="""
Sets the new grid load for the anker solar bank
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

from pooranker import Solarbank
from utils.samples import get_columns_from_csv

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(__file__))


async def anker_home_load_set(sb: Solarbank, home_load: int) -> bool:
    logger.info(f'anker_home_load_set started "{home_load}"')

    try:
        is_done = await sb.set_home_load(home_load)
    except:
        is_done = False
    if is_done:
        logger.debug("anker solarbank grid load set.")
    else:
        logger.error("anker solarbank grid load not set.")
        
    logger.info(f"anker_home_load_set finished {'ok' if is_done else 'with problem'}")        
    return is_done


async def main(sb: Solarbank, samples: int) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.info(f'Samples from stdin are not valid')
        return 10

    """ The normalised smartmeter power """
    smp = c['SMP']
    if smp.size != samples:
        logger.error(f'Wrong number of smartmeter records "{smp.size}"')
        return 11
    
    """ The normalised solarbqnk power output """
    sbpo = c['SBPO']
    if sbpo.size != samples:
        logger.error(f'Wrong number of smartmeter records "{sbpo.size}"')
        return 12
        
    """ The normalised inverter power samples channel 1 """
    ivp1 = c['IVP1']
    """ The normalised inverter power samples channel 2 """
    ivp2 = c['IVP2']
    """ The normalised inverter power sum """
    ivp = ivp1 + ivp2
    if ivp.size != samples:
        logger.error(f'Wrong number of smartmeter records "{ivp.size}"')
        return 13
    
    """ The normalised smartplug power """
    spph = c['SPPH']
    if spph.size != samples:
        logger.error(f'Wrong number of smartmeter records "{spph.size}"')
        return 14

    goal = smp
    if (spph>0.0).any():
        logger.info(f'Using smartplug records')
        goal += spph
    elif (ivp>0.0).any():
        logger.info(f'Using inverter records')
        goal += ivp
    elif (sbpo>0.0).any():
        logger.info(f'Using solarbank records')
        goal += sbpo

    # Weighted average
    grid_goal = int((2*goal.min()+goal.mean())/3)
    # Adapt to system limits
    grid_goal = min(max(grid_goal,100), 800)
    
    logger.info(f'Calculated grid goal for solarbank "{grid_goal:.0f}W"')
    is_done = await anker_home_load_set(sb, grid_goal)
    logger.info(f"Setting of grid load {'ok' if is_done else 'failed'}")

    return 0 if is_done else 15


@dataclass
class Script_Arguments:
    power_samples: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description='Set the grid load of the solarbank',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--power_samples', type = int, default = 5,
                        help = "Number of recorded samples to use")
    
    
    args = parser.parse_args()

    return Script_Arguments(args.power_samples)


if __name__ == '__main__':
    args = parse_arguments()

    sb = Solarbank()

    try:
        err = asyncio.run(main(sb, args.power_samples))
    except ClientConnectorError:
        logger.error('Cannot connect to solarbank.')
        err = 9
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_home_load_set_once done (err={err}).')
    sys.exit(err)
