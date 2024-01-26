#!/usr/bin/env python3

__doc__="""Tries to make most of the available solar energies in my house.

The system consists of two 440 VAp solar panels, an Anker Solix 1600
powerbank, an APsystems EZ1M inverter, an Tuya Antella smartplug. The
smartplug were not needed if the 'Local Mode' of the inverter had not
disappeared after firmware change during the powerbank integration.

The power imported from the net is measured by a Hitchi optical sensor
attached to my distributor's measurement device using Tasmota. Energy
exported to the net cannot be measured though. As a result when the
power is displayed as '0' there is more electricity produced than
consumed.

The powerbank sometimes does not behave as what one could expect from
the configuration in the Anker app, especially in terms of power
delivery. Anyway the powerbank cannot provide less than 100W to the
house if it provides something at all. Especially during the night the
house requires less, sometimes even less than 50W. The difference is
lost. In this case propably also more power for the operating of the
solar equipment is needed than required for house. At the end it will
propably pay off to prevent the powerbank to deliver the 100W as long
as it is not empty. It may be cheaper to use energy from the net in
these periods and keep the battery stored power for times when the
equipment in the house can actually consume it.

If the solar system cannot deliver power to the house the it is stored
in the powerbank.

This script is designed to be run by cron every 15 minutes. It
calculates the average of the consumed power in the house during the
last 15 minutes from the recorded data read from stdin. If the average
is below the 100W then the solar system is prevented from importing
the power into the house by opening the switch of the
smartplug. Otherwise the switch is closed.
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
                                    ss_command: Switch_Status) -> Switch_Status:

    logger.info(f'tuya_smartplug_switch_set started')
    is_closed = await (sp.turn_on() if ss_command.value == "Closed" else sp.turn_off())
    logger.info(f'tuya_smartplug_switch_set done')        
    ss_result = Switch_Status('Closed' if is_closed else 'Open')
    logger.info(f'Switch is "{ss_result}".')
    return ss_result


async def main(sp: Smartplug,
               switch_power_mean: f64,
               switch_power_std: f64,
               switch_samples: int, f: Any) -> int:

    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPP'.split(',')
    df = pd.read_csv(f, sep = sep, names = names).tail(switch_samples)

    """ The last recorded house smartmeter power """
    smp = np.array(df.SMP.apply(str2f64))
    if np.isnan(smp).any():
        logger.error(f'Undefined SMP samples')
        return 1

    sm_mean, sm_std = smp.mean(), smp.std()
    logger.info(f'Stats of last records: mean "{sm_mean:.0f}", std "{sm_std:.0f}"')

    # Switch to be opened if below average and standard deviation
    is_below = sm_mean < switch_power_mean and sm_std < switch_power_std
    ss_command = Switch_Status('Open' if is_below else 'Closed')
    logger.info(f'Tuya smartplug switch command is "{ss_command}"')
    
    try:
        ss_result = await tuya_smartplug_switch_set(sp, ss_command) 
    except ClientConnectorError:
        logger.error('Cannot connect to smartplug.')
        return 1

    # ss_result and ss_command to be the same 
    logger.info(f'Tuya smartplug switch result is "{ss_result}"')
    
    return 0


@dataclass
class Script_Arguments:
    plug_name: str
    switch_power_mean: f64
    switch_power_std: f64
    switch_samples: int
    
def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest power values from Tasmota Smartmeter and APsystems EZ1M inverter',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--plug_name', type = str, required = True,
                        help = "Name of the Tuya smartplug")

    parser.add_argument('--switch_power_mean', type = f64, default = 100.0,
                        help = "Minimum power output mean of powerbank")

    parser.add_argument('--switch_power_std', type = f64, default = 50.0,
                        help = "Minimum power output deviation of powerbank")

    parser.add_argument('--switch_samples', type = int, default = 15,
                        help = "Number of recorded samples to use")
    
    args = parser.parse_args()
    
    return Script_Arguments(args.plug_name,
                            args.switch_power_mean,
                            args.switch_power_std,
                            args.switch_samples)


if __name__ == '__main__':
    logger.info(f'"MAIN" started')
    args = parse_arguments()
    err = asyncio.run(main(Smartplug(args.plug_name),
                           args.switch_power_mean,
                           args.switch_power_std,
                           args.switch_samples,
                           sys.stdin))

    logger.info(f'"MAIN" done (err = {err})')
    sys.exit(err)
