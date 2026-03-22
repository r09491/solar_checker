#!/usr/bin/env python3

__doc__="""Sets the power output of the anker solarbank to the home
grid from 100W to 800W. During discharge the solix needs four
minutes. During charge/bypass it takes one minutes.  There are
conditions when the solix does not comply with the request without any
warning. An obvious one is if the irradation is below the request with
a lack of power. If the battery is full all the power from the solar
panels via MPPT is passed directly to the grid. This holds also if the
temperature is below 4 degrees or the battery does not charge in
general. """

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

import numpy as np

from pooranker import Solarbank
from utils.samples import get_columns_from_csv

from aiohttp.client_exceptions import ClientConnectorError

from dataclasses import dataclass

async def anker_home_load_set(sb: Solarbank, home_load: int) -> bool:
    try:
        is_done = await sb.set_home_load(home_load)
    except:
        is_done = False
    if is_done:
        logger.info("home load is set.")
    else:
        logger.warning("home load is rejected.")
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
    sbpo_mean = int(sbpo.mean())
    
    """ The normalised solarbank power output """
    sbpb = c['SBPB']
    if sbpb.size != samples:
        logger.error(f'wrong number of solarbank records "{sbpb.size}"')
        return -15
    sbpb_mean = int(sbpb.mean())

    """ The normalised solarbank battery SOC """
    sbsb = c['SBSB']
    if sbsb.size != samples:
        logger.error(f'wrong number of SOC records "{sbsb.size}"')
        return -16
    sbsb_mean = sbsb.mean()

    """ The normalised solarbank power input """
    ivp1 = c['IVP1']
    if ivp1.size != samples:
        logger.error(f'wrong number of solarbank records "{ivp1.size}"')
        return -17
    ivp2 = c['IVP2']
    if ivp2.size != samples:
        logger.error(f'wrong number of solarbank records "{ivp2.size}"')
        return -18
    ivp = ivp1+ivp2
    ivp_mean = int(ivp.mean())
    
    logger.info(f'{sbpi} sbpi')
    logger.info(f'{sbpb} sbpb')
    logger.info(f'{sbpo} sbpo')
    logger.info(f'{ivp} ivp')
    logger.info(f'{smp} smp')
        
    if (smp > 500).any(): # Only during BYPASS/DISCHARGE
        estimate = 200 if int(sbpb[-1]) > 0 else 800
        logger.info(f'Burst (SMP >500) required!')
        return estimate

    if abs(smp[-1]) <10:
        logger.info(f"SMP small! Keep setting!")
        return -20

    if  abs(np.diff(smp)[-1]) >40:
        logger.info(f"SMP change large! Keep setting!")
        return -21

    """
    During the home load setting the solarbank output and the inverter
    output may become inconsistent. The inverter output is more
    current since it is local. The solarbank output is late since it
    updated in the cloud. Let the previous trial settle first!
    """
    if  abs(np.diff(ivp)[-1]) >40:
        logger.info(f"IVP change large (no burst)! Keep setting!")
        return -22

    # if  (not ivp.any()) and abs(np.diff(sbpo)[-1]) >40:
    #     logger.info(f"SBPO change large! Keep setting!")
    #     return -23
    if  abs(np.diff(sbpo)[-1]) >40:
        logger.info(f"SBPO change large (no burst)! Keep setting!")
        return -23
    
    if (not ivp.any()) and (ivp > sbpo).any(): 
        logger.info(f"IVP > SBPO!  Keep setting!")
        return -24
    
    """ Do not change home load if irradiance changes are too
    high. The solix may not be able to follow via cloud. Irradiance
    changes the battery compenstates by addapting charge/discharge
    power. Home load setting mainly changes if grid power changes.
    """
    if  abs(np.diff(sbpi)[-1]) >40:
        logger.info(f"SBPI change large! Keep setting!")
        return -25

    if ((sbpb>0) & (sbpb<90)).any():
        logger.info(f"SBPB volatile! Keep setting!")
        return -26                

    estimate =  + smp[-1] + (sbpo[-1] if sbpo[-1]>0 else ivp[-1])
    # estimate =  smp[-1] + (ivp[-1] if ((ivp[-1] >0) and
    #                                    (sbpi>0).all()
    #                                    ) else sbpo[-1])
    if estimate < 100:
        logger.info(f"Plug devices to minimize power export!")

    """ Limit discharge """
    ubound = 200 if sbpb_mean > 0 else 800
    estimate = int(min(max(estimate,100), ubound))
    logger.info(f"Proposal is '{estimate}W'")

    if (sbpi[-1] > 0) and  (estimate > (sbpi[-1]-sbpb[-1])): #Bypass/Charge
        logger.warning(f"Cannot comply!")
        #estimate = int(sbpi[-1])

    return  estimate # My solix only uses one channel


async def main(sb: Solarbank, samples: int) -> int:

    estimate = await get_home_load_estimate(samples)
    if estimate < 0:
        return estimate
    
    logger.info(f'home load goal is "{estimate:.0f}"')
    is_done = await anker_home_load_set(sb, estimate)
    logger.info(f"home load goal is {'set' if is_done else 'kept'}")

    # After a burst post actions shall occur immediately 
    return 0 if (is_done and estimate<800) else 1


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
    except OSError:
        logger.error('cannot access store file')
        err = -99        
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'done with (err={err}).')
    sys.exit(err)
