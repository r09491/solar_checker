#!/usr/bin/env python3

__doc__="""
Sets the new home load for the anker solar bank
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

from pooranker import Solarbank
from utils.samples import get_columns_from_csv

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

async def anker_home_load_set(sb: Solarbank, home_load: int) -> bool:
    logger.info(f'anker_home_load_set begin"')

    try:
        is_done = await sb.set_home_load(home_load)
    except:
        is_done = False
    if is_done:
        logger.info("home load is set.")
    else:
        logger.warning("home load is not set.")
        
    logger.info(f"anker_home_load_set end")        
    return is_done


async def get_home_load_estimate(samples: int) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.info(f'samples from stdin are not valid')
        return -10

    """ The normalised smart meter power """
    smp = c['SMP']
    if smp.size != samples:
        logger.error(f'wrong number of smart meter records "{smp.size}"')
        return -11
    smp_mean = int(smp.mean())

    """ The normalised solarbank power input """
    sbpi = c['SBPI']
    if sbpi.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpi.size}"')
        return -12
    sbpi_mean = int(sbpi.mean())
    
    """ The normalised solarbank power output """
    sbpb = c['SBPB']
    if sbpb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpb.size}"')
        return -13
    sbpb_mean = int(sbpb.mean())

    """ The normalised solarbank power output """
    sbpo = c['SBPO']
    if sbpo.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpo.size}"')
        return -14

    """ The normalised inverter power samples channel 1 """
    ivp1 = c['IVP1']
    """ The normalised inverter power samples channel 2 """
    ivp2 = c['IVP2']
    """ The normalised inverter power sum """
    ivp = ivp1 + ivp2
    if ivp.size != samples:
        logger.error(f'wrong number of smartmeter records "{ivp.size}"')
        return -15

    logger.info(f'{sbpi} sbpi')
    logger.info(f'{sbpb} sbpb')
    logger.info(f'{sbpo} sbpo')
    logger.info(f'{ivp} ivp')

    if not sbpo.any() and not sbpb.any():
        logger.info(f'bank in STANDBY, defaulting!')
        return 100

    if not sbpo.all():
        logger.info(f'bank in TRANSITION, defaulting!')
        return 100

    if sbpb[sbpb>0].any():
        logger.info(f'bank in DISCHARGE, defaulting!')
        return 100

    """
    Data in local mode are faster acquired than those from the
    cloud. Here the cloud solar bank data are at least one minute
    older than those of the local inverter. After some time the data
    will stabilize and look reasonable at least, ie values from
    solarbank are larger than those of the inverter. Home load value
    shall only be set in stable situation.
    """
    if (ivp[-2:] > (sbpo + 10)[-2:]).any(): # Some tolerance for roundings ...
        logger.error(f'bank in ERROR')
        return -16

        
    # Use data from the solarbank to set data in the solarbank
    voted = smp + sbpo 
    logger.info(f'using solarbank power')
    
    # Weighted average (last samples have more influence)
    estimate = int(sum((2**w)*v for w, v in enumerate(voted)) /
                   sum(2**w for w, v in enumerate(voted)))
    logger.info(f"home load proposal is '{estimate}W'")
    
    if (sbpb > 0).all(): 
        logger.info(f'bank in DISCHARGE.')
    elif (sbpb < 0).all(): 
        logger.info(f'bank in CHARGE.')
    else:
        logger.info(f'bank in BYPASS')
            
    return min(max(estimate,100), 800) # My solix only uses one channel


async def main(sb: Solarbank, samples: int) -> int:

    estimate = await get_home_load_estimate(samples)
    if estimate < 0:
        return estimate
    
    logger.info(f'home load goal is "{estimate:.0f}"')
    is_done = await anker_home_load_set(sb, estimate)
    logger.info(f"home load goal is {'set' if is_done else 'kept'}")

    return 0 if is_done else 1


@dataclass
class Script_Arguments:
    power_samples: int

def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description='Set the home load of the solarbank',
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
        logger.error('cannot connect to solarbank.')
        err = -9
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'done with (err={err}).')
    sys.exit(err)
