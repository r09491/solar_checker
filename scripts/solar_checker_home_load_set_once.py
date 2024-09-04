#!/usr/bin/env python3

__doc__="""
Sets the new home load for the anker solar bank
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
    logger.info(f'anker_home_load_set begin"')

    try:
        is_done = await sb.set_home_load(home_load)
    except:
        is_done = False
    if is_done:
        logger.info("solarbank home load set.")
    else:
        logger.warning("anker solarbank home load not set.")
        
    logger.info(f"anker_home_load_set end")        
    return is_done


async def get_home_load_estimate(samples: int) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.info(f'samples from stdin are not valid')
        return 0

    """ The normalised smart meter power """
    smp = c['SMP']
    if smp.size != samples:
        logger.error(f'wrong number of smart meter records "{smp.size}"')
        return 0
    smp_mean = int(smp.mean())
    
    """ The normalised solarbank power input """
    #sbpi = c['SBPI']
    #if sbpi.size != samples:
    #    logger.error(f'wrong number of solarbank records "{sbpi.size}"')
    #    return 0
    
    """ The normalised solarbank power output """
    sbpo = c['SBPO']
    if sbpo.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpo.size}"')
        return 0

    """ The normalised solarbank charge power """
    sbpb = c['SBPB']
    if sbpb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpb.size}"')
        return 0
    sbpb_mean = int(sbpb.mean())
    
    """ The normalised solarbank battery status """
    sbsb = c['SBSB']
    if sbsb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbsb.size}"')
        return 0
    sbsb_mean = 100 * int(sbsb.mean())
    
    """ The normalised inverter power samples channel 1 """
    ivp1 = c['IVP1']
    """ The normalised inverter power samples channel 2 """
    ivp2 = c['IVP2']
    """ The normalised inverter power sum """
    ivp = ivp1 + ivp2
    if ivp.size != samples:
        logger.error(f'wrong number of smartmeter records "{ivp.size}"')
        return 0
    
    """ The normalised smartplug power """
    spph = c['SPPH']
    if spph.size != samples:
        logger.error(f'wrong number of smartmeter records "{spph.size}"')
        return 0

    estimate = smp # !! Shared !!
    if (sbpo>0.0).any():
        estimate += sbpo
    elif (ivp>0.0).any():
        estimate += ivp
    elif (spph>0.0).any():
        estimate += spph

    # Weighted average
    estimate = int(sum((2**w)*v for w, v in enumerate(estimate)) /
                   sum(2**w for w, v in enumerate(estimate)))
    logger.info(f"home load proposal is '{estimate}W'")

    if sbpb_mean < 0: # Charging
        logger.info(f'Battery is charging')

        ##if ((smp_mean + sbpb_mean) < -600):
        ## estimate = 100 # Ignored!

    elif sbpb_mean > 0: # Discharging
        logger.info(f'Battery is discharged')

    else:
        logger.info(f'Battery is passed by')
        ##estimate = 100 # Ignored
        
    return min(max(estimate,100), 800)


async def main(sb: Solarbank, samples: int) -> int:

    estimate = await get_home_load_estimate(samples)
    if estimate == 0:
        return 10
    
    logger.info(f'home load goal is "{estimate:.0f}W"')
    is_done = await anker_home_load_set(sb, estimate)
    logger.info(f"home load goal is {'ok' if is_done else 'failed'}")

    return 0 if is_done else 15


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
        err = 9
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_home_load_set_once end (err={err}).')
    sys.exit(err)
