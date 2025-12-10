__doc__="""
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
import asyncio

import numpy as np
import pandas as pd

from dataclasses import dataclass

from ..typing import(
    List, Optional, f64
)
from ..csvlog import(
    get_logdays,
    get_predict_power_log
)

async def get_hour_log(
        logday: str,
        logprefix: str,
        logdir: str
) -> pd.DataFrame:
    log = await get_predict_power_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir
    )

    return log.set_index('TIME').resample('h').mean()


async def get_predict_tables(
        casthours: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    casthours = casthours.resample('3h').mean()

    starts = casthours.index.strftime("%H:00")
    stops = casthours.index.shift(1).strftime("%H:00")
    start_stop_df = pd.DataFrame({"START":starts, "STOP":stops})

    sbsb_df = casthours["SBSB"]
    sbsb_df.reset_index(inplace=True, drop=True)
    
    casthours.drop("SBSB", inplace=True, axis=1)
    casthours.reset_index(inplace=True, drop=True)
    
    watts_table = pd.concat(
        [start_stop_df, casthours],
        axis=1
    )
    energy_table = pd.concat(
        [start_stop_df, 3*casthours.cumsum(), 100*sbsb_df],
        axis=1
    )
    
    return (watts_table, energy_table)


"""
Simulates the Anker Solix generation 1 power part
"""
async def simulate_solix_1_w(
        log: pd.DataFrame,
        ratio: f64
) -> None:

    # Cast irridiance samples by scaling
    issbpi = log["SBPI"] >0
    log.loc[issbpi, "SBPI"] *= ratio

    # Simultate low irradiance
    issbpi = log["SBPI"] <35 
    log.loc[issbpi, "SBPB"] = -log.loc[issbpi, "SBPI"]
    log.loc[issbpi, "SBPO"] = 0

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >=35) & (log["SBPI"] <100)
    log.loc[issbpi,"SBPB"] = 0
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]

    # constrain high irradiance
    issbpi = (log["SBPI"] > 800)
    log.loc[issbpi,"SBPI"] = 800

    # Simultate bright irradiance
    issbpi = (log["SBPI"] >=100) & (log["SBPI"] <=800)
    log.loc[issbpi,"SBPB"] = -log.loc[issbpi,"SBPI"] + 100
    log.loc[issbpi,"SBPO"] = log.loc[issbpi,"SBPI"] + log.loc[issbpi,"SBPB"]


"""
Simulates the Anker Solix generation 1 energy part
"""
async def simulate_solix_1_wh(
        log: pd.DataFrame,
        realsoc: f64
) -> None:

    # Current SOC of the power bank
    log_wh = (log["SBPB"].cumsum()-realsoc*1600)

    # Simulate battery full
    isfull = log_wh < -1600
    log.loc[isfull,"SBPB"] = 0
    log.loc[isfull,"SBPO"] = log.loc[isfull, "SBPI"]

    # Simulate battery empty
    isempty = log_wh >-160
    log.loc[isempty,"SBPB"] = 0
    log.loc[isempty,"SBPO"] = 0

    # Update SOC
    log["SBSB"] = -log_wh/1600
    
    
@dataclass
class Script_Arguments:
    logprefix: str
    logdir: str

async def predict_naive(
        args: Script_Arguments
) -> (pd.DataFrame, pd.Timestamp, pd.Timestamp):
    
    days = await get_logdays(
        logprefix = args.logprefix,
        logdir = args.logdir
    )
    if days is None:
        logger.error("Failed to get logdays")
        return None

    pastday, today = days[-2:]
    logger.info(f'Predicting "{today}" using "{pastday}"')

    pastday, todaylog = await asyncio.gather(
        get_hour_log(
            logday = pastday,
            logprefix = args.logprefix,
            logdir = args.logdir
        ),
        get_hour_log(
            logday = today,
            logprefix = args.logprefix,
            logdir = args.logdir
        )
    )

    # Abort if a cast is not possible
    if len(todaylog.index) >= len(pastday.index):
        # No cast is possible at the end of today
        return todaylog, None, None

    
    # Do the cast

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[0]
    
    # Adapt the cast indices
    pastday.index = pd.date_range(
        todaylog.index[0].date(),
        periods=24,
        freq="h"
    )

    # Calc prediction data
    realstop = pastday.index[len(todaylog.index)-1]
    caststart = pastday.index[len(todaylog.index)]
    reallast = todaylog.loc[realstop ,"SBPI"]
    castlast = pastday.loc[realstop ,"SBPI"]
    adaptratio = reallast/castlast if castlast >0.0 else 0.0
    
    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last cast start is "{caststart}"')
    logger.info(f'Last real irridiance is "{reallast}"')
    logger.info(f'Last cast irridiance is "{castlast}"')
    logger.info(f'Last real/cast ratio is "{adaptratio}"')
    
    # The restlog needs adaptation
    restlog = pastday.copy().loc[caststart:,:]
    # Adapt the restlog to the current irridiance
    if adaptratio >0.0:
        await simulate_solix_1_w(
            restlog, adaptratio
        )
    
    #Join the current real data with the cast data
    castlog = pd.concat([todaylog,restlog])
    #Ensure the plausibility of cast
    await simulate_solix_1_wh(
        castlog, realsoc
    )

    return castlog, realstop, caststart
