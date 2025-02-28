#!/usr/bin/env python3

__doc__="""Tries to zeroise the power from the grid and to the grid

A HITCHI infrared sensor polls the electricity provider's grid power
sensor of a house with PV.  A positive value indicates the current
import from the grid, a negative one the current export to the
grid. Ideally the value is zero.
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

from aiohttp.client_exceptions import ClientConnectorError

import numpy as np

##from utils.typing import f64, f64s, t64, t64s, timeslots
##from utils.samples import get_columns_from_csv

from dataclasses import dataclass
##from typing import Any, Optional

from tasmota import Smartmeter
from pooranker import Solarbank

SBPL_STEP = 10
SBPL_MIN = 100
SBPL_MAX = 800
SBPL_N = 4

async def get_grid_power(
        q: asyncio.Queue,
        sm_ip: str,
        sm_port: int,
        sm_delay:int
) -> None:

    smp_old = 0
    smps =  SBPL_N*[0]

    sm = Smartmeter(sm_ip, sm_port)

    while True:
        sm_status = await sm.get_status_sns()
        smp = 0 if sm_status is None else sm_status.power
        smps = smps[1:] + [smp]
        smp_new = int(sum(smps)/len(smps))
        if abs(smp_new-smp_old)>SBPL_STEP:
            if q.full():
                await q.get()
            if q.empty():
                await q.put(smp_new)
            logger.info(f'queued grid delta "{smp_new}W"')
            smp_old = smp_new
        await asyncio.sleep(sm_delay)



async def set_home_load_load(
        q: asyncio.Queue,
        sb_delay_sun:int,
        sb_delay_bat:int,
        sm_delay:int
) -> None:
    
    sb = Solarbank()

    sb_delay = sb_delay_sun # sb_delay_bat
    while True:
        logger.info('waiting for grid delta')
        smp_mean = await q.get()
        logger.info(f'dequeued grid delta "{smp_mean}W"')

        # Get the data from the solarbank
        sbdata = await sb.get_power_data()
        if sbdata is None: continue

        # Get the old power data
        sbpo = int(sbdata.output_power)

        # Calc the new load 
        sbpl = SBPL_STEP*int((sbpo+smp_mean)/SBPL_STEP)
        sbpl = min(max(SBPL_MIN, sbpl),SBPL_MAX)
        logger.info(f'home load SBPL proposed "{sbpl}W"')
        
        # Calc bank setting time for power from sun or battery
        sbpi = int(sbdata.output_power)
        sb_delay = sb_delay_sun if sbpi>0 else sb_delay_bat

        sbpb = int(sbdata.battery_power)
        if (sbpi<sbpl) and (sbpb <= 0):
            logger.info(f'sun SBPI "{sbpi}W" too low, no zeroise, do best!')
        if (sbpi>sbpl) and (sbpb <= 0):
            logger.info(f'sun SBPI "{sbpi}W" may allow zeroise!')
        if (sbpb>=0) and (sbpb<sbpl) and (sbpi == 0):
            logger.info(f'bat SBPB "{sbpb}W" too low, no zeroise, do best!')
        if (sbpb>=0) and (sbpb>sbpl) and (sbpi == 0):
            logger.info(f'bat SBPB "{sbpb}W" may allow zeroise!')

        # Set the new home load
        logger.info(f'home load goal SBPL "{sbpl}W" commanded')
        is_done = await sb.set_home_load(sbpl)
        logger.info(f"home load goal SBPL is {'set' if is_done else 'kept'}")

        sb_delay = sb_delay if is_done else SBPL_N*sm_delay
        logger.info(f'granting "{sb_delay}s" to settle')
        await asyncio.sleep(sb_delay)


async def zeroise(
        sm_ip: str,
        sm_port: int,
        sm_delay:int,
        sb_delay_sun:int,
        sb_delay_bat:int
) -> None:

    smp_queue = asyncio.Queue(maxsize = 1)
    
    await asyncio.gather(
        set_home_load_load(smp_queue, sb_delay_sun, sb_delay_bat, sm_delay),
        get_grid_power(smp_queue, sm_ip, sm_port, sm_delay)
    )


@dataclass
class Script_Arguments:
    sm_ip: str
    sm_port: int
    sm_delay: int
    sb_delay_sun: int
    sb_delay_bat: int
    
async def main(args: Script_Arguments) -> int:

    if not 3 <= args.sm_delay <= 60:
        logger.error(f'Smartmeter delay illegal value "{args.sm_delay}"')
        return -1

    if not 60 <= args.sb_delay_sun <= 360:
        logger.error(f'Solarbank sun delay illegal value "{args.sb_delay_sun}"')
        return -2

    if not 180 <= args.sb_delay_bat <= 480:
        logger.error(f'Solarbank bat delay illegal value "{args.sb_delay_bat}"')
        return -3

    
    await zeroise(
        args.sm_ip,
        args.sm_port,
        args.sm_delay,
        args.sb_delay_sun,
        args.sb_delay_bat
    )
    
    return 0


def parse_arguments() -> Script_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description='Zeroise the power grid',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument('--sm_ip', type = str, default = 'tasmota',
                        help = "IP address of the Tasmota smartmeter")

    parser.add_argument('--sm_port', type = int, default = 80,
                        help = "IP port of the Tasmota smartmeter")
    
    parser.add_argument('--sm_delay', type = int, default = 3,
                        help = "Delay for the polling of the smartmeter")

    parser.add_argument('--sb_delay_sun', type = int, default = 60,
                        help = "Delay for the setting of the homeload during sun")

    parser.add_argument('--sb_delay_bat', type = int, default = 240,
                        help = "Delay for the setting of the homeload during bat")
    
    args = parser.parse_args()

    return Script_Arguments(
        args.sm_ip,
        args.sm_port,
        args.sm_delay,
        args.sb_delay_sun,
        args.sb_delay_bat
    )


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'started')
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt:
        err = 99
    logger.info(f'done (err={err})')
    sys.exit(err)
