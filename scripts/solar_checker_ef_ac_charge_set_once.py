#!/usr/bin/env python3

__doc__="""
Sets the Ecoflow Delta Marge AC charge watts to balance grid power for zero input
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

from aiohttp.client_exceptions import (
    ClientConnectorError
)

from ecoflow import (
    Delta_Max,
    MIN_GRID_WATTS,
    MAX_GRID_WATTS,
    MIN_CHARGE_WATTS,
    MAX_CHARGE_WATTS,
)
from utils.samples import (
    get_columns_from_csv
)

from dataclasses import dataclass


async def get_grid_watts_delta(samples: int, mingridp: int, maxgridp:int) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.error(f'samples from stdin are not valid')
        return None

    """ The normalised smart meter power """
    smp = c['SMP']
    if smp.size != samples:
        logger.error(f'wrong number of smart meter records "{smp.size}"')
        return MAX_GRID_WATTS
    
    """ The normalised solarbank power output """
    sbpb = c['SBPB']
    if sbpb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpb.size}"')
        return -13
    sbpb_mean = int(sbpb.mean())
    if sbpb_mean > 0:
        logger.info(f'battery discharge, reduce')
        return MAX_GRID_WATTS # Force min charge rate
    
    """ The normalised solarbank power input """
    sbpi = c['SBPI']
    if sbpi.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpi.size}"')
        return -12
    sbpi_mean = int(sbpi.mean())
    if sbpi_mean == 0:
        logger.info(f'no irradiation, reduce')
        return MAX_GRID_WATTS # Force min charge rate
        
    smp_mean = min(max(mingridp,int(smp.mean())),maxgridp)
    logger.info(f'grid watts delta mean "{smp_mean}W"')
    return smp_mean


async def main(dm: Delta_Max,
               samples: int,
               mingridp: int,
               maxgridp: int,
               minchargep: int,
               maxchargep: int) -> int:

    smp = await get_grid_watts_delta(samples, mingridp, maxgridp)
    balance = await dm.set_ac_charge_watts_balance(smp, minchargep, maxchargep)
    if balance is None: 
        logger.info(f"Balance charging rate not modified")
        return 1 # ok

    return 0


@dataclass
class Script_Arguments:
    power_samples: int
    min_grid_watts: int
    max_grid_watts: int
    min_charge_watts: int
    max_charge_watts: int


def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=__name__, 
        description='Set the AC charge rate of the Delta Max',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--power_samples', type = int, default = 5,
                        help = "Number of recorded samples to use")
    
    parser.add_argument('--min_grid_watts', type = int, default = MIN_GRID_WATTS,
                        help = "Minimum grid_watts for balance")

    parser.add_argument('--max_grid_watts', type = int, default = MAX_GRID_WATTS,
                        help = "Maximum grid_watts for balance")
    
    parser.add_argument('--min_charge_watts', type = int, default = MIN_CHARGE_WATTS,
                        help = "Minimum charge watts for balance")

    parser.add_argument('--max_charge_watts', type = int, default = MAX_CHARGE_WATTS,
                        help = "Maximum charge_watts for balance")

    args = parser.parse_args()
    return Script_Arguments(args.power_samples,
                            args.min_grid_watts,
                            args.max_grid_watts,
                            args.min_charge_watts,
                            args.max_charge_watts)

if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'started.')
    
    dm = Delta_Max()

    try:
        err = asyncio.run(
            main(dm,
                 args.power_samples,
                 args.min_grid_watts,
                 args.max_grid_watts,
                 args.min_charge_watts,
                 args.max_charge_watts
            )
        )
    except ClientConnectorError:
        logger.error('cannot connect to solarbank.')
        err = -9
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'done with (err={err}).')
    sys.exit(err)
