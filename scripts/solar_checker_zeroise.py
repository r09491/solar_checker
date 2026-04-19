#!/usr/bin/env python3

__doc__="""Tries to zeroise the power imported from the grid against
exported to the grid.

A HITCHI infrared sensor polls the electricity provider's smartmeter.
A positive value indicates the import from the grid, a negative one
the export to the grid. Ideally the value is zero. The big advantage
is the data are on the local net. This means low latency compared to
cloud aquisition.

An Apsystems EZ1-M inverter outputs the power to the grid. The big
advantage is the powerv value is available on the local net. This
means low latency compared to cloud aquisition.

An Anker Solix 1 solarbank delivers power from the PV panels or
battery to the inverter.  The big disadvantage is data are on the
cloud only. This means high latency. The funny thing is that changes
in the solarbank are reported upto four minutes later than by the
smartmeter and the inverter. However setting the data like 'home load'
occurs immediately though the associated data show up minutes later
after they have found their way back from China.

Short latency allows to implment zeroising (within 10W) in the low
seconds range. At least if the power comes the PV panels and the
sun. The battery discharge is another story. Here it takes up to four
minutes to bring the solarbank output into the commanded range. But
this is an hardware issue and not a software issue.

This script was tested on my system only.
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import os
import sys
import argparse
import asyncio
import time
import datetime

from dataclasses import dataclass

from tasmota import Smartmeter
from apsystems import Inverter
from pooranker import Solarbank

SAMPLE_N = 2 # Number of sensor samples to calc mean of samples
LOADS_N = 2  # Number of samples to calc mean of load average

SMP_ZERO = 15 # Threshold which considers system as zeroised
SMP_STEP = 50 # Rapid grid changes

IVP_ZERO = 5 # Cancel noise
IVP_STEP = 50 # Rapid radiation changes
SBPL_MIN = 100
SBPL_MAX = 800
SBPL_WIN = 1.07 # 1.05

SBPL_BURST = 500

SBPL_PANEL_DAY_START = datetime.time(7, 0)
SBPL_PANEL_DAY_END = datetime.time(19, 0)
SBPL_PANEL_DELAY = 60
SBPL_BATTERY_DELAY = 210

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
        logger.debug(f'SMP {smp_mean}W queued')

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
        logger.debug(f'IVP "{ivp_mean}W" queued')

        now = time.time()
        later = iv_delay*(int(now/iv_delay) + 1)
        await asyncio.sleep(later-now)


def get_home_load_delay() -> int:
    # It is assumed that battery is discharged in the night only
    now = datetime.datetime.now().time()
    is_day = SBPL_PANEL_DAY_START <= now < SBPL_PANEL_DAY_END
    sbpl_delay = SBPL_PANEL_DELAY if is_day else SBPL_BATTERY_DELAY 
    logger.info(f'SBPL delay {sbpl_delay}s')
    return sbpl_delay

async def set_home_load_power(
        q: asyncio.Queue
) -> None:

    sb = Solarbank()

    sbpl_set, sbpl_old = SBPL_MIN, SBPL_MIN
    is_done = False

    recall = 0
    while True:
        logger.info(f'Waiting for home load')
        sbpl_new = await q.get()
        if sbpl_new is None:
            logger.warning(f'SBPL illegal value')
            continue
        logger.info(f'SBPL {sbpl_new}W dequeued')

        await q.put(sbpl_new) # Block
        logger.info(f'SBPL {sbpl_new}W load received')

        is_load = (((abs(sbpl_new - sbpl_set) >SMP_ZERO) and
                   (abs(sbpl_new - sbpl_old) >SMP_ZERO))) # New load
        if is_load:
            recall = 0
            logger.info(f'SBPL {sbpl_new}W sent to SB')
            is_done = await sb.set_home_load(sbpl_new)
            logger.info(f'SBPL {"set" if is_done else "kept"} in SB')

        else: #Avoid future 'kept' messages
            recall += 1
            logger.info(f'SBPL {sbpl_new}W load skipped')
            sbpl_new = sbpl_set # Keep the first
            logger.info(f'SBPL {sbpl_new}W load refixed')

            logger.info(f'Cannot zeroise @ {recall}! Manage devices!')

        sbpl_old = sbpl_new
            
        # Block a recall for the given time. The solarbank needs the
        # time to actually implment the requested load internally. if
        # the power is delivered from the MPPT this is a matter of
        # seconds. If the power originates from the battery it is a
        # matter of minutes and a recall is required to extend the
        # delay.

        if is_done:
            sbpl_delay = get_home_load_delay() 
            logger.info(f'--> Block setting "{sbpl_delay}s"')
            await asyncio.sleep(sbpl_delay) #Wait
            logger.info(f'<-- Unblock setting "{sbpl_delay}s"')
            sbpl_set = sbpl_new
            is_done = False
        
        await q.get() # Unblock

        
async def to_stdout(text: str):
    #loop = asyncio.get_running_loop()
    #await loop.run_in_executor(None, sys.stdout.write, text)
    #await loop.run_in_executor(None, sys.stdout.flush)
    sys.stdout.write( text)
    sys.stdout.flush()

async def schedule(
        sm_q: asyncio.Queue,
        iv_q: asyncio.Queue,
        sb_q: asyncio.Queue,
        cycle_delay: int,
        show_samples: int
) -> None:

    sbpl_news = []
    
    smp_new, ivp_new, sbpl_new = SBPL_MAX, SBPL_MAX, SBPL_MAX
    
    cycle, sbpl_old, ivp_sum, smp_sum = 0, SBPL_MIN, 0, 0

    while True:
        smp_old, ivp_old = smp_new, ivp_new

        now = time.time()
        
        logger.info(f'Waiting for power values')
        smp_new, ivp_new = await asyncio.gather(sm_q.get(), iv_q.get())
        logger.info(f'SMP {smp_new}W, IVP {ivp_new}W dequeued ')

        logger.info(f'SMP_NEW  {smp_new:4.0f}  {ivp_new:4.0f}  IVP_NEW')
        logger.info(f'SMP_OLD  {smp_old:4.0f}  {ivp_old:4.0f}  IVP_OLD')

        
        cycle += 1 

        # The SMP error is negative if power is exported to the
        # grid. The SMP error is positive if power is imported
        # from the grid. The goal is to make the SMP error zero by
        # mainpulting the home load
        smp_sum += smp_new
        smp_cycle_mean = int(smp_sum/cycle)
        smp_cycle_error = smp_cycle_mean
        logger.info(f'SMP cyle delta {smp_cycle_error}W @ {cycle}')

        # The IVP error is negative if the SB cannot provide the
        # power the load was set to. Obviously one reason may be
        # the home load is set to high. Or the PV panels do not
        # provide enough power due to cloud cover etc.
        ivp_sum += ivp_new
        ivp_cycle_mean = int(ivp_sum/cycle)
        ivp_cycle_error = ivp_cycle_mean - sbpl_old 
        logger.info(f'IVP cyle delta {ivp_cycle_error}W @ {cycle}')

        # Both errors indicate losses if the observed power
        # outputs do not meet the logic correct requested load

        
        sbpl_new = None
        
        if (ivp_new <= IVP_ZERO):
            if ((sbpl_old > SBPL_MIN)):
                logger.info(f'IVP zero! Oh no!')
                sbpl_new = SBPL_MIN
                sbp_news = [] # Use load! No Average
            else:
                logger.info(f'IVP rezero! No setting!')

        elif (smp_new >SBPL_BURST):
            if ((sbpl_old < SBPL_BURST)):
                logger.info(f'SMP burst! Caution!')
                sbpl_new = SBPL_MAX
                sbp_news = [] # Use load! No Average
            else:
                logger.info(f'SMP reburst! No setting!')
            
        elif abs(smp_new) <SMP_ZERO:
            logger.info(f'SMP small! No setting! Is {sbpl_old}W! Bravo!')

            ### The goals is achieved ###

        elif (abs(ivp_new - ivp_old) >IVP_STEP):
            logger.info(f'IVP change large! Delay setting!')

        elif (abs(smp_new - smp_old) >SMP_STEP):
            logger.info(f'SMP change large! Delay setting!')

        else:
            ivp_goal = int(ivp_new)
            sbp_goal = int(SBPL_WIN*(smp_new+ivp_goal))
            sbpl_new = min(max(sbp_goal, SBPL_MIN), SBPL_MAX)
            sbpl_news = (sbpl_news + [sbpl_new])[-LOADS_N:] 
            sbpl_new = int(sum(sbpl_news)/len(sbpl_news))
            logger.info(f'SBPL new ==> {sbpl_new}W @ {len(sbpl_news)}')

            if abs(sbpl_new - sbpl_old) < SMP_ZERO:
                logger.info(f'SBPL same! No setting! Devices?')
                sbpl_new = None

        if sbpl_new is not None:
            logger.info(f'SBPL last ==> {sbpl_new}W')

            logger.info(f'SBPL {sbpl_new}W queued')
            if sb_q.full():  # Skip new load
                sbpl_new = await sb_q.get()
                logger.info(f'Old setting {sbpl_new}W in progress! Wait!')
            await sb_q.put(sbpl_new)
            
            # Reset the statistics
            cycle, sbpl_old, ivp_sum, smp_sum = 0, sbpl_new, 0, 0

        else:
            # Reset the loads list
            sbpl_news = []
            sbpl_new = sbpl_old
            
        if show_samples >0:
            now_str = time.strftime("%H:%M:%S", time.localtime(now))
            text = f'{now_str} '
            text += f'{smp_new:+5d} {ivp_new:3d}  '
            text += f'{smp_cycle_error:+4d} {ivp_cycle_error:+4d}  '
            text += f'{sbpl_old:3d}  '
            text += f'{cycle}'
            await to_stdout(text+'\n')
            #await to_stdout(text+'\r')

        
        # Delay without thrift
        later = cycle_delay*(int(now/cycle_delay) + 1)
        await asyncio.sleep(later-now)


async def zeroise(
        sm_ip: str,
        sm_port: int,
        sm_delay:int,
        iv_ip: str,
        iv_port: int,
        iv_delay:int,
        cycle_delay:int,
        show_samples: int
) -> None:

    sm_queue = asyncio.Queue(maxsize = 1)
    iv_queue = asyncio.Queue(maxsize = 1)
    sb_queue = asyncio.Queue(maxsize = 1)

    zeroise_tasks =[
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
            sb_queue
        ),
        schedule(
            sm_queue,
            iv_queue,
            sb_queue,
            cycle_delay,
            show_samples
        )
    ]
    await asyncio.gather(
        *zeroise_tasks
    )

@dataclass
class Script_Arguments:
    sm_ip: str
    sm_port: int
    iv_ip: str
    iv_port: int
    cycle_delay: int
    show_samples: int

async def main(args: Script_Arguments) -> int:

    if not 10 <= args.cycle_delay <= 60:
        logger.error(f'Cycle delay illegal value "{args.cycle_delay}"')
        return -1

    await zeroise(
        args.sm_ip,
        args.sm_port,
        args.cycle_delay/2,
        args.iv_ip,
        args.iv_port,
        args.cycle_delay/2,
        args.cycle_delay,
        args.show_samples
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
    
    parser.add_argument('--cycle_delay', type = int, default = 10,
                        help = "Delay for calculating the home load")

    parser.add_argument('--show_samples', type = int, default = 1,
                        help = "Control the output of power samples")

    args = parser.parse_args()

    return Script_Arguments(
        args.sm_ip,
        args.sm_port,
        args.iv_ip,
        args.iv_port,
        args.cycle_delay,
        args.show_samples
    )


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'Zeroise started')
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt:
        err = 99
    logger.info(f'Zeroise done (err={err})')
    sys.exit(err)
