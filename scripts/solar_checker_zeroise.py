#!/usr/bin/env python3

__doc__="""Tries to zeroise the power from the grid and to the grid

A HITCHI infrared sensor polls the electricity provider's grid power
sensor of a house with PV.  A positive value indicates the current
import from the grid, a negative one the current export to the
grid. Ideally the value is zero. The big advantage is data are from
the local net. This means low latency compared to cloud aquisition.

An Apsystems EZ1-M inverter puts the power into the house net. The big
advantage is data are from the local net. This means low latency
compared to cloud aquisition.

An Anker Solix 1 solarbank delivers power from the PV panels or
battery to the inverter.  The big disadvantage is data are from the
cloud. This means high latency compared to local aquisition. It shows
that changes in the solarbank are deteted upto four minutes earlier
using the smartmeter and the inverter. As a result they are out of
scope. However setting the data like 'home load' occurs immediately
though the associated data show this minutes later.

This allows to implment zeroising (within 10W) in the low seconds
range at least if the power source are the PVpanels.

The battery discharge is another story. Here it takes up to four
minutes to bring the solarbank output into the commanded range.
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

from dataclasses import dataclass

from tasmota import Smartmeter
from apsystems import Inverter
from pooranker import Solarbank

SAMPLE_N = 4

async def get_grid_power(
        q: asyncio.Queue,
        sm_ip: str,
        sm_port: int,
        sm_delay:int
) -> None:

    smps =  SAMPLE_N*[0]

    sm = Smartmeter(sm_ip, sm_port)

    while True:
        sm_status = await sm.get_status_sns()
        smp = 0 if sm_status is None else sm_status.power
        smps = smps[1:] + [smp]
        smp_mean = int(sum(smps)/len(smps))

        if q.full():
            await q.get()
        await q.put(smp_mean)
        logger.debug(f'queued grid SMP "{smp_mean}W"')

        await asyncio.sleep(sm_delay)

    
async def get_inverter_power(
        q: asyncio.Queue,
        iv_ip: str,
        iv_port: int,
        iv_delay:int
) -> None:

    ivps =  SAMPLE_N*[0]

    iv = Inverter(iv_ip, iv_port)

    while True:
        output = await iv.get_output_data()
        ivp1 = 0 if output is None else output.p1
        ivp2 = 0 if output is None else output.p2
        ivp = ivp1 + ivp2
        ivps = ivps[1:] + [ivp]
        ivp_mean = int(sum(ivps)/len(ivps))

        if q.full():
            await q.get()
        await q.put(ivp_mean)
        logger.debug(f'queued grid IVP "{ivp_mean}W"')

        await asyncio.sleep(iv_delay)


SMP_OK = 10
SMP_STEP = 50

IVP_ZERO = 0
IVP_STEP = 40

SBPL_MIN = 100
SBPL_MAX = 800        
SBPL_WIN = 1.05

async def get_estimate(
        smp_new: int,
        ivp_new: int,
        smp_old: int,
        ivp_old: int
) -> int | None:

    logger.info(f'SMP_NEW {smp_new:4.0f} {ivp_new:4.0f}   IVP_NEW')
    logger.info(f'SMP_OLD {smp_old:4.0f} {ivp_old:4.0f}   IVP_OLD')
    
    if (smp_new >SBPL_MAX) and (smp_old <SBPL_MAX):
        logger.info(f'SMP burst! Set immediately')
        return SBPL_MAX

    if (smp_new >SBPL_MAX) and (smp_old >SBPL_MAX):
        logger.info(f'SMP burst! No setting!')
        return None

    if abs(smp_new) <SMP_OK:
        logger.info(f'SMP small! No setting!')
        return None

    if (abs(smp_new - smp_old) >SMP_STEP):
        logger.info(f'SMP change large! No setting!')
        return None

    if (abs((smp_new + ivp_new) < SBPL_MIN) and
            ((smp_old + ivp_old) < SBPL_MIN)):
        logger.info(f'SMP/IVP stable! No setting!')
        return None
    
    ivp_goal = int(ivp_new)
    sbp_goal = int(SBPL_WIN*(smp_new+ivp_goal))
    sbp_load = min(max(sbp_goal, SBPL_MIN), SBPL_MAX)
    logger.info(f'Load estimate SBPL: "{sbp_load}W"')
    return sbp_load


async def set_home_load_load(
        sm_q: asyncio.Queue,
        iv_q: asyncio.Queue,
        sb_delay:int
) -> None:
    
    sb = Solarbank()

    smp_new, ivp_new = SBPL_MAX, SBPL_MAX 

    while True:
        smp_old, ivp_old = smp_new, ivp_new
        
        logger.debug(f'Waiting for power values')
        smp_new, ivp_new = await asyncio.gather(sm_q.get(), iv_q.get())
        logger.debug(f'dequeued SMP "{smp_new}W", IVP "{ivp_new}W"')

        sbp_load = await get_estimate(smp_new, ivp_new, smp_old, ivp_old)
        if sbp_load is None:
            continue # SBPL setting canceled

        # Set the new home load
        logger.info(f'SBPL "{sbp_load}W" sent to solarbank')
        is_done = await sb.set_home_load(sbp_load)
        logger.info(f'SBPL {"set" if is_done else "kept"} in solarbank')
        
        logger.info(f'granting the solarbank "{sb_delay}s" to settle')
        await asyncio.sleep(sb_delay)


async def zeroise(
        sm_ip: str,
        sm_port: int,
        sm_delay:int,
        iv_ip: str,
        iv_port: int,
        iv_delay:int,
        sb_delay:int
) -> None:

    smp_queue = asyncio.Queue(maxsize = 1)
    ivp_queue = asyncio.Queue(maxsize = 1)
    
    await asyncio.gather(
        get_inverter_power(
            ivp_queue,
            iv_ip,
            iv_port,
            iv_delay
        ),
        get_grid_power(
            smp_queue,
            sm_ip,
            sm_port,
            sm_delay
        ),
        set_home_load_load(
            smp_queue,
            ivp_queue,
            sb_delay
        )
    )


@dataclass
class Script_Arguments:
    sm_ip: str
    sm_port: int
    sm_delay: int
    iv_ip: str
    iv_port: int
    iv_delay: int
    sb_delay: int

async def main(args: Script_Arguments) -> int:

    if not 3 <= args.sm_delay <= 30:
        logger.error(f'Smartmeter delay illegal value "{args.sm_delay}"')
        return -1

    if not 3 <= args.iv_delay <= 30:
        logger.error(f'Inverter delay illegal value "{args.iv_delay}"')
        return -1

    if not 0 <= args.sb_delay <= 480:
        logger.error(f'Solarbank sun delay illegal value "{args.sb_delay}"')
        return -3

    await zeroise(
        args.sm_ip,
        args.sm_port,
        args.sm_delay,
        args.iv_ip,
        args.iv_port,
        args.iv_delay,
        args.sb_delay
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
    
    parser.add_argument('--sm_delay', type = int, default = 4,
                        help = "Delay for the polling of the smartmeter")

    parser.add_argument('--iv_ip', type = str, default = 'apsystems',
                        help = "IP address of the Apsystems inverter")

    parser.add_argument('--iv_port', type = int, default = 8050,
                        help = "IP port of the Apsystems inverter")
    
    parser.add_argument('--iv_delay', type = int, default = 4,
                        help = "Delay for the polling of the inverter")

    parser.add_argument('--sb_delay', type = int, default = 30,
                        help = "Delay after the setting of the homeload")
    
    args = parser.parse_args()

    return Script_Arguments(
        args.sm_ip,
        args.sm_port,
        args.sm_delay,
        args.iv_ip,
        args.iv_port,
        args.iv_delay,
        args.sb_delay
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
