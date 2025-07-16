#!/usr/bin/env python3

__doc__="""Sets the power output from 100W to 800W of the anker
solarbank to the home grid. During discharge the solix needs four
minutes. During charge/bypass it takes one minutes.  There are
conditions when the solix does not comply with the request without any
warning. An obvious one is if the irradation is below the request with
a lack of power. If the battery is full all the power from the solar
panels via MPPT is passed directly to the grid. This holds also if the
temperature is below 4 degrees or the battery does not charge in
general.

The script does not consider inconsistencies of of solarbank and
inverter samples.
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
    sbpo = c['SBPO']
    if sbpo.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpo.size}"')
        return -13
    if sbpo[-1] == 0:
        logger.error(f'Solarbank has no output.')
        return -18
    sbpo_mean = int(sbpo.mean())
    
    """ The normalised solarbank power output """
    sbpb = c['SBPB']
    if sbpb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpb.size}"')
        return -14
    sbpb_mean = int(sbpb.mean())

    """ The normalised solarbank battery SOC """
    sbsb = c['SBSB']
    if sbsb.size != samples:
        logger.error(f'wrong number of SOC records "{sbsb.size}"')
        return -15
    sbsb_mean = sbsb.mean()

    """ The normalised solarbank power input """
    ivp1 = c['IVP1']
    if ivp1.size != samples:
        logger.error(f'wrong number of solarbank records "{ivp1.size}"')
        return -16
    ivp2 = c['IVP2']
    if ivp2.size != samples:
        logger.error(f'wrong number of solarbank records "{ivp2.size}"')
        return -17
    ivp = ivp1+ivp2
    ivp_mean = int(ivp.mean())
    

    logger.info(f'{sbpi} sbpi')
    logger.info(f'{sbpb} sbpb')
    logger.info(f'{sbpo} sbpo')
    logger.info(f'{ivp} ivp')

    if (sbpb > 0).all(): 
        logger.info(f'bank in DISCHARGE.')
    elif (sbpb < 0).all(): 
        logger.info(f'bank in CHARGE.')
    elif (sbpi>0).all():
        logger.info(f'bank in BYPASS')
    else:
        logger.info(f'bank in STANDBY')

        
    if (int(smp[-1]) > 800): # Only during BYPASS/DISCHARGE
        estimate = 300 if int(sbpb[-1]) > 0 else 800
        logger.info(f'Burst required "{estimate}"')
        return estimate

    
    KP, KI, KD = 0.5, 0.1, 0.3
    logger.info(f"KP {KP}, KI {KI}, KD {KD}")
    P, I, D = KP*smp[-1], KI*smp.sum(), KD*(smp[-1]-smp[0])
    logger.info(f"P {P:.0f}, I {I:.0f}, D {D:.0f}")
    PID = P + I + D
    logger.info(f"PID {PID:.0f}")

    estimate = (ivp[-1] if ivp[-1]>0 else sbpo[-1]) + PID
    logger.info(f"home load proposal is '{estimate:.0f}W'")
    
    ubound = 200 if sbpb_mean > 0 else 800
    estimate = 10*int(min(max(estimate,100), ubound)/10)
    logger.info(f"constraint proposal is '{estimate}W'")

    if (estimate>sbpi_mean and sbpb_mean <= 0): #Bypass/Charge
        logger.info(f"Cannot comply!")
        return -20
        
    return  estimate # My solix only uses one channel


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
        prog=__name__, ##os.path.basename(__file__),
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
