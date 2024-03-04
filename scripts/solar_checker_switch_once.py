#!/usr/bin/env python3

__doc__="""Tries to make most of the available solar energies in my house.

A solar system consists of two 440 VAp solar panels, an Anker Solix
1600 powerbank, an APsystems EZ1M inverter, and a Tuya smartplug. The
smartplug were not needed if the 'Local Mode' of the inverter were
available and had not disappeared after firmware change during the
powerbank integration.

The power imported from the net is measured by a Tasmota compatible
Hitchi optical sensor attached to a distributor's measurement
equipment. This can only measure imported energy. As a result when the
power is displayed as '0' there is more electricity produced than
consumed. This is called a lost.

The powerbank sometimes does not behave as one could expect from the
configuration in the Anker app, especially in terms of power
delivery. Anyway it cannot provide less than 100W to the house if it
provides something at all. Especially during the night the house
requires less, sometimes even less than 50W. The difference is
lost. In this case propably also more power for the operating of the
solar equipment is needed than required for house. At the end it will
propably pay off to prevent the powerbank to deliver the 100W as long
as it is not empty. It may be cheaper to use energy from the net in
these periods and keep the battery stored power for times when the
equipment in the house can actually consume it.

This script is designed to be run by cron every 15 minutes. It
calculates the average of the consumed power in the house during the
last 15 minutes from the recorded data read from stdin. If the mean is
below 'power_mean_open' and the standard deviation is within the range
of the 'power_mean_deviation ' then the solar system is prevented from
importing the power into the house by opening the switch of the
plug. If the mean is above 'power_mean_closed' and the standard
deviation in the range of the 'power_mean_deviation ' then the solar system
is connected to house can provide power.

For example this can be used to keep the switch open during the night
and the battery is not dicharged. Otherwise more power were put into
the net than my house requires.
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
               power_mean_open: f64,
               power_mean_closed: f64,
               power_mean_deviation: f64,
               power_samples: int, f: Any) -> int:

    c = await get_columns_from_csv()
    if c is None:
        logger.info(f'Samples from stdin  not valid')
        return 10

    smp = c['SMP']
    if smp.size != power_samples:
        logger.error(f'Wrong number of records "{spbo.size}"')
        return 11
    smp_mean, smp_std = smp.mean(), smp.std()
    logger.info(f'Last records power mean "{smp_mean:.0f}W", std "{smp_std:.0f}W"')
    
    sbpo = c['SBPO']
    if sbpo.size != power_samples:
        logger.error(f'Wrong number of records "{spbo.size}"')
        return 12
    solarp = sbpo

    ivp = c['IVP1'] + c['IVP2']
    if ivp.size != power_samples:
        logger.error(f'Wrong number of records "{ivp.size}"')
        return 13
    solarp = ivp if (ivp>0).any() else solarp

    spph = c['SPPH']
    if spph.size != power_samples:
        logger.error(f'Wrong number of records "{spph.size}"')
        return 14
    solarp = spph if (spph>0).any() else solarp 
            
    solarp_mean, solarp_std = solarp.mean(), solarp.std()
    logger.info(f'Last records solar mean "{solarp_mean:.0f}W", std "{solarp_std:.0f}W"')

    ss_actual = await tuya_smartplug_switch_get(sp)
    logger.info(f'The smartplug switch currently is "{ss_actual}"')

    # Switch to be Open if below average and standard deviation
    is_to_open =  solarp_mean < power_mean_open and solarp_std < power_mean_deviation
    # Switch to be Closed if above average and standard deviation
    is_to_closed =  solarp_mean > power_mean_closed and solarp_std < power_mean_deviation and \
        smp_mean < 25 and smpp_std < power_mean_deviation

    # What has to be done now?
    ss_desired = Switch_Status('Open' if is_to_open else
                               'Closed' if is_to_closed else ss_actual)
    
    if ss_actual != ss_desired:
        logger.info(f'The smartplug switch is desired to "{ss_desired}"')
        try:
            ss_result = await tuya_smartplug_switch_set(sp, ss_desired) 
        except ClientConnectorError:
            logger.error('Cannot connect to smartplug.')
            return 1
        # ss_result and ss_desired to be the same 
        logger.info(f'The smartplug switch became "{ss_result}"')
            
    else:
        logger.info(f'The smartplug switch remains "{ss_actual}"')

    return 0


@dataclass
class Script_Arguments:
    plug_name: str
    power_mean_open: f64
    power_mean_closed: f64
    power_mean_deviation: f64
    power_samples: int
    
def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from Tasmota Smartmeter and APsystems EZ1M inverter',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    parser.add_argument('--power_mean_open', type = f64, default = 100.0,
                        help = "Total power to disconnect the solar system from house")

    parser.add_argument('--power_mean_closed', type = f64, default = 100.0,
                        help = "Total power to connect the solar system from house")

    parser.add_argument('--power_mean_deviation', type = f64, default = 25.0,
                        help = "Minimum power output deviation of powerbank")

    parser.add_argument('--power_samples', type = int, default = 10,
                        help = "Number of recorded samples to use")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.plug_name,
                            args.power_mean_open,
                            args.power_mean_closed,
                            args.power_mean_deviation,
                            args.power_samples)


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'Switching of "{args.plug_name}" started')
    
    if args.power_mean_open > args.power_mean_closed:
        logger.error(f'Contradicting power means "{args.power_mean_open}" > "{args.power_mean_closed}"')
        sys.exit(1)
    
    err = asyncio.run(main(Smartplug(args.plug_name),
                           args.power_mean_open,
                           args.power_mean_closed,
                           args.power_mean_deviation,
                           args.power_samples,
                           sys.stdin))

    logger.info(f'Switching of "{args.plug_name}" done (err={err})')
    sys.exit(err)
