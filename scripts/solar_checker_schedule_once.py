#!/usr/bin/env python3

__doc__="""Tries to make most of the available solar energies in my house.

The balkony solar system consists of two 440 VAp solar panels, an
Anker Solix 1600 powerbank, an APsystems EZ1M inverter, an Tuya
Antella smartplug. The smartplug were not needed if the 'Local Mode'
of the inverter were available and had not disappeared after not
confirmed firmware change during the powerbank integration.

The power imported from the net is measured by a Tasmota compatible
Hitchi optical sensor attached to my distributor's measurement
equipment. Only imported energy can be measured not the exported. As a
result when the power is displayed as '0' there is more electricity
produced than consumed. Ia call this lost.

The powerbank sometimes does not behave as one could expect from the
configuration in the Anker app, especially in terms of power
delivery. Anyway the powerbank cannot provide less than 100W to the
house if it provides something at all. Especially during the night the
house requires less, sometimes even less than 50W. The difference is
lost. In this case propably also more power for the operating of the
solar equipment is needed than required for house. At the end it will
propably pay off to prevent the powerbank to deliver the 100W as long
as it is not empty. It may be cheaper to use energy from the net in
these periods and keep the battery stored power for times when the
equipment in the house can actually consume it.

If the solar system cannot deliver power to the house it is stored
in the powerbank.

This script is designed to be run by cron every 15 minutes. It
calculates the average of the consumed power in the house during the
last 15 minutes from the recorded data read from stdin. If the average
is below the 80W and the standard deviation below 40W then the solar
system is prevented from importing the power into the house by opening
the switch of the smartplug. Otherwise the switch remains closed or is
closed again.

In my house the selected mean and standard deviation guarantee that
the switch remains open during the night and the battery is not
dicharged. Otherwise more power were put into the net than my house
requires.
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"


import os
import sys
import argparse
import asyncio

from aiohttp.client_exceptions import ClientConnectorError

import numpy as np
import pandas as pd

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
    
f64 = np.float64
def str2f64(value: str) -> f64:
    return f64(value)


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
               power_deviation: f64,
               power_samples: int, f: Any) -> int:

    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPP'.split(',')
    df = pd.read_csv(f, sep = sep, names = names).tail(power_samples)
    logger.info(f'Using {df.shape[0]} records with {df.shape[1]} columns')

    if df.shape[0] != power_samples:
        logger.error(f'Wrong number of records "{df.shape[0]}"')
        return 10
    if df.shape[1] != len(names):
        logger.error(f'Wrong number of record columns "{df.shape[1]}"')
        return 11

    
    """ The last records from the house smartmeter """
    smp = np.array(df.SMP.apply(str2f64))
    """ The last records from the smartplug at inverter"""
    spp = np.array(df.SPP.apply(str2f64))
    """ The total power """
    tp = smp + spp
    
    tp_mean, tp_std = tp.mean(), tp.std()
    logger.info(f'Last records mean "{tp_mean:.0f}W", std "{tp_std:.0f}W"')

    ss_actual = await tuya_smartplug_switch_get(sp)
    logger.info(f'The smartplug switch currently is "{ss_actual}"')

    # Switch to be Open if below average and standard deviation
    is_to_open = tp_mean < power_mean_open and tp_std < power_deviation
    # Switch to be Closed if below average and standard deviation
    is_to_closed = tp_mean > power_mean_closed and tp_std < power_deviation

    # What has to be done now?
    ss_desired = Switch_Status('Open' if is_to_open else
                               'Closed' if is_to_closed else None)
    
    if ss_desired is not None and ss_actual != ss_desired:
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
    power_deviation: f64
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
                        help = "House power to disconnect the solar system from house")

    parser.add_argument('--power_mean_closed', type = f64, default = 100.0,
                        help = "House power to connect the solar system from house")

    parser.add_argument('--power_deviation', type = f64, default = 25.0,
                        help = "Minimum power output deviation of powerbank")

    parser.add_argument('--power_samples', type = int, default = 15,
                        help = "Number of recorded samples to use")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.plug_name,
                            args.power_mean_open,
                            args.power_mean_closed,
                            args.power_deviation,
                            args.power_samples)


if __name__ == '__main__':
    logger.info(f'"MAIN" started')
    args = parse_arguments()

    if args.power_mean_open > args.power_mean_closed:
        logger.error(f'Contradicting powers "{args.power_mean_open}" > "{args.power_mean_closed}"')
        sys.exit(1)
    
    err = asyncio.run(main(Smartplug(args.plug_name),
                           args.power_mean_open,
                           args.power_mean_closed,
                           args.power_deviation,
                           args.power_samples,
                           sys.stdin))

    logger.info(f'"MAIN" done (err = {err})')
    sys.exit(err)
