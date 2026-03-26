#!/usr/bin/env python3

__doc__="""Tries to zeroise the power import from the grid and the
export to the grid

A HITCHI infrared sensor polls the electricity provider's grid power
sensor in a house with a PV.  A positive value indicates the current
import from the grid, a negative one the current export to the
grid. Ideally the value is zero. The big advantage is the data are
on the local net. This means low latency compared to cloud
aquisition.

An Apsystems EZ1-M inverter puts the power into the grid. The big
advantage is the data are on the local net. This means low latency
compared to cloud aquisition.

An Anker Solix 1 solarbank delivers power from the PV panels or
battery to the inverter.  The big disadvantage is data are on the
cloud. This means high latency compared to local aquisition. It shows
that changes in the solarbank are reporteded upto four minutes later
by the smartmeter than by the inverter. However setting the data like
'home load' occurs immediately though the associated data show up
minutes later after they have found their way back from China.

Short latency allows to implment zeroising (within 10W) in the low
seconds range at least if the power source are the PV panel and the
sun. The battery discharge is another story. Here it takes up to four
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
import time

from dataclasses import dataclass

from tasmota import Smartmeter
from apsystems import Inverter
from pooranker import Solarbank

SAMPLE_N = 6
LOADS_N = 24

SMP_OK = 10
SMP_STEP = 40

IVP_ZERO = 3 # Cancel noise

SBPL_MIN = 100
SBPL_MAX = 800
SBPL_WIN = 1.07 # 1.05


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
        logger.debug(f'queued grid SMP {smp_mean}W')

        now = time.time()
        later = sm_delay*(int(now/sm_delay) + 1)
        await asyncio.sleep(later-now)

    
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

        now = time.time()
        later = iv_delay*(int(now/iv_delay) + 1)
        await asyncio.sleep(later-now)


async def set_home_load_power(
        q: asyncio.Queue,
        sb_delay:int
) -> None:

    sb = Solarbank()

    sbpl_set = SBPL_MAX
    
    while True:
        logger.debug(f'Waiting for home load')
        sbpl_new = await q.get()
        logger.debug(f'dequeued solarbank SBPL {sbpl_new}W')

        if sbpl_new is None: # Robustness
            sbpl_new = SBPL_MIN
        
        elif abs(sbpl_new - sbpl_set) <SMP_OK:
            logger.info(f'SBPL old! No setting!')
            continue

        logger.info(f'SBPL {sbpl_new}W sent to SB')
        is_done = await sb.set_home_load(sbpl_new)
        logger.info(f'SBPL {"set" if is_done else "kept"} in SB')

        await q.put(sbpl_new) # Block
        if is_done:
            logger.info(f'SB is granted "{sb_delay}s" to settle')
            await asyncio.sleep(sb_delay)
        sbpl_set = await q.get() # Unblock

async def schedule(
        sm_q: asyncio.Queue,
        iv_q: asyncio.Queue,
        sb_q: asyncio.Queue,
        cycle_delay:int
) -> None:

    sbp_loads = []
    
    smp_new, ivp_new, sbp_load = SBPL_MAX, SBPL_MAX, SBPL_MAX
    
    cycle, sbp_load_cycle, ivp_cycle_sum, smp_cycle_sum = 0, SBPL_MIN, 0, 0

    while True:
        smp_old, ivp_old = smp_new, ivp_new
        
        logger.debug(f'Waiting for power values')
        smp_new, ivp_new = await asyncio.gather(sm_q.get(), iv_q.get())
        logger.debug(f'dequeued SMP {smp_new}W, IVP {ivp_new}W')

        logger.info(f'SMP_NEW  {smp_new:4.0f}  {ivp_new:4.0f}  IVP_NEW')
        logger.info(f'SMP_OLD  {smp_old:4.0f}  {ivp_old:4.0f}  IVP_OLD')

        sbp_load = None
        
        if ((ivp_new <= IVP_ZERO) and
            (ivp_old > IVP_ZERO)):
            logger.info(f'IVP zero start! Reset!')
            sbp_load = SBPL_MIN

        elif ((ivp_new <= IVP_ZERO) and
            (ivp_old <= IVP_ZERO)):
            logger.info(f'IVP zero continued! No setting!')

        elif (smp_new >SBPL_MAX) or (smp_old >SBPL_MAX):
            logger.info(f'SMP burst started! Set immediately')
            sbp_load = SBPL_MAX

        # elif (smp_new >SBPL_MAX) and (smp_old >SBPL_MAX):
        #     logger.info(f'SMP burst continued! No setting!')

        elif abs(smp_new) <SMP_OK:
            logger.info(f'SMP small! No setting! Is {sbp_load_cycle}W! Bravo!')

            ### The goals is achieved ###

            cycle += 1 

            # The SMP error is negative if power is exported to the
            # grid. The SMP error is positive if power is imported
            # from the grid. The goal is to make the SMP error zero by
            # mainpulting the home load
            smp_cycle_sum += smp_new
            smp_cycle_mean = int(smp_cycle_sum/cycle)
            smp_cycle_error = smp_cycle_mean
            logger.info(f'SMP cyle error {smp_cycle_error}W @ {cycle}')

            # The IVP error is negative if the SB cannot provide the
            # power the load was set to. Obviously one reason may be
            # the home load is set to high. Or the PV panels do not
            # provide enough power due to cloud cover etc.
            ivp_cycle_sum += ivp_new
            ivp_cycle_mean = int(ivp_cycle_sum/cycle)
            ivp_cycle_error = ivp_cycle_mean - sbp_load_cycle 
            logger.info(f'IVP cyle error {ivp_cycle_error}W @ {cycle}')

            # Both errors indicate losses if the observed power
            # outputs do not meet the logic correct requested load

        elif (abs(smp_new - smp_old) >SMP_STEP):
            logger.info(f'SMP change large! No setting!')

        else:
            ivp_goal = int(ivp_new)
            sbp_goal = int(SBPL_WIN*(smp_new+ivp_goal))
            sbp_load = min(max(sbp_goal, SBPL_MIN), SBPL_MAX)

        if sbp_load is not None:
            logger.info(f'SBPL last ==> {sbp_load}W')

            sbp_loads = (sbp_loads + [sbp_load])[-LOADS_N:] 
            sbp_load = int(sum(sbp_loads)/len(sbp_loads))
            logger.info(f'SBPL mean ==> {sbp_load}W @ {len(sbp_loads)}')
            
            logger.debug(f'SBPL {sbp_load}W queued')
            if sb_q.full():  
                # Skip new load
                sbp_load = await sb_q.get()
                logger.info(f'Old setting {sbp_load}W in progress! Wait!')
            await sb_q.put(sbp_load)
            
            # Reset the statistics
            cycle, sbp_load_cycle, ivp_cycle_sum, smp_cycle_sum = 0, sbp_load, 0, 0

        else:
            # Reset the loads list
            sbp_loads = []
            
        # Delay without thrift
        now = time.time()
        later = cycle_delay*(int(now/cycle_delay) + 1)
        await asyncio.sleep(later-now)


async def zeroise(
        sm_ip: str,
        sm_port: int,
        sm_delay:int,
        iv_ip: str,
        iv_port: int,
        iv_delay:int,
        sb_delay:int,
        cycle_delay:int
) -> None:

    sm_queue = asyncio.Queue(maxsize = 1)
    iv_queue = asyncio.Queue(maxsize = 1)
    sb_queue = asyncio.Queue(maxsize = 1)
    
    await asyncio.gather(
        get_inverter_power(
            iv_queue,
            iv_ip,
            iv_port,
            iv_delay
        ),
        get_grid_power(
            sm_queue,
            sm_ip,
            sm_port,
            sm_delay
        ),
        set_home_load_power(
            sb_queue,
            sb_delay
        ),
        schedule(
            sm_queue,
            iv_queue,
            sb_queue,
            cycle_delay
        )
    )


@dataclass
class Script_Arguments:
    sm_ip: str
    sm_port: int
    iv_ip: str
    iv_port: int
    sb_delay: int
    cycle_delay: int

async def main(args: Script_Arguments) -> int:

    if not 0 <= args.sb_delay <= 480:
        logger.error(f'Solarbank sun delay illegal value "{args.sb_delay}"')
        return -1
    if not 6 <= args.cycle_delay <= 480:
        logger.error(f'Cycle delay illegal value "{args.cycle_delay}"')
        return -2

    await zeroise(
        args.sm_ip,
        args.sm_port,
        args.cycle_delay,
        args.iv_ip,
        args.iv_port,
        args.cycle_delay,
        args.sb_delay,
        args.cycle_delay
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
    
    parser.add_argument('--iv_ip', type = str, default = 'apsystems',
                        help = "IP address of the Apsystems inverter")

    parser.add_argument('--iv_port', type = int, default = 8050,
                        help = "IP port of the Apsystems inverter")
    
    parser.add_argument('--sb_delay', type = int, default = 60,
                        help = "Delay after the setting of the home load")
    
    parser.add_argument('--cycle_delay', type = int, default = 6,
                        help = "Delay for calculating the home load")

    args = parser.parse_args()

    return Script_Arguments(
        args.sm_ip,
        args.sm_port,
        args.iv_ip,
        args.iv_port,
        args.sb_delay,
        args.cycle_delay
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
