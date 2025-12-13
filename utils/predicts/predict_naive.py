__doc__=""" Predicts the samples of an Anker Solix 1 powerbank for the
rest of today assuming they are similar to those of the passed
days. Changes in the hourly irridances for the rest of today are
calculated from ratio of the latest irridiance of today to that of the
passed days """

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
from ..common import(
    PREDICT_POWER_NAMES
)
from ..csvlog import(
    get_windowed_logs
)

LOGWINDOWSIZE = 2
async def get_hour_logs(
        logprefix: str,
        logdir: str,
        logwindow: int = LOGWINDOWSIZE
) -> (pd.DataFrame, pd.DataFrame):

    # Get the logs close to the forecast day
    logdays, logs = await get_windowed_logs(
        logwindow = logwindow,
        logprefix = logprefix,
        logdir = logdir,
        usecols = PREDICT_POWER_NAMES
    )

    # Make hour logs from the the minute logs
    logs = [l.set_index('TIME').resample('h').mean() for l in logs]

    # The forcastday is at the end of the list
    todaylog = logs[-1]

    # Make a single log from the many passed logs
    
    pastlogs = pd.concat(
        [l.reset_index(drop=True) for l in logs[:-1]]
    )
    
    pastlog = pastlogs.groupby(pastlogs.index).mean()

    pastlog.index = pd.date_range(
        todaylog.index[0].date(),
        periods=24,
        freq="h"
    ).set_names('TIME')

    return logdays[-1], pastlog, todaylog

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
async def simulate_solix_1_power_w(
        log: pd.DataFrame
):


    # Simultate low irradiance
    issbpi = (log["SBPI"] >0) & (log["SBPI"] <=35) 
    log.loc[issbpi, "SBPB"] = -log.loc[issbpi, "SBPI"]
    log.loc[issbpi, "SBPO"] = 0

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >35) & (log["SBPI"] <=100)
    log.loc[issbpi,"SBPB"] = 0
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]

    # constrain high irradiance
    issbpi = (log["SBPI"] > 800)
    log.loc[issbpi,"SBPI"] = 800

    # Simultate bright irradiance
    issbpi = (log["SBPI"] >100) & (log["SBPI"] <=800)
    log.loc[issbpi,"SBPB"] = -log.loc[issbpi,"SBPI"] + 100
    log.loc[issbpi,"SBPO"] = log.loc[issbpi,"SBPI"] + log.loc[issbpi,"SBPB"]


"""
Simulates the Anker Solix generation 1 energy part
"""
async def simulate_solix_1_energy_wh(
        log: pd.DataFrame,
        realsoc: f64,
        full_wh: f64 = -1600,
        empty_wh: f64 = -160
):

    # Current SOC of the power bank
    log_wh = (log["SBPB"].cumsum()+realsoc*full_wh)

    # Simulate battery full
    isfull = log_wh <full_wh
    log.loc[isfull,"SBPB"] = 0
    log.loc[isfull,"SBPO"] = log.loc[isfull, "SBPI"]

    # Simulate battery empty
    isempty = log_wh >empty_wh
    log.loc[isempty,"SBPB"] = 0
    log.loc[isempty,"SBPO"] = 0

    # Update SOC
    log["SBSB"] = log_wh/full_wh
    
    
@dataclass
class Script_Arguments:
    logprefix: str
    logdir: str

async def predict_naive_today(
        args: Script_Arguments
) -> (pd.DataFrame, pd.Timestamp, pd.Timestamp):

    today, pastlog, todaylog = await get_hour_logs(
        logprefix = args.logprefix,
        logdir = args.logdir
    )

    # Abort if a cast is not possible
    if len(todaylog.index) >= len(pastlog.index):
        # No cast is possible at the end of today
        return todaylog, None, None

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[-1]

    # Calc prediction data
    realstop = pastlog.index[len(todaylog.index)-1]
    caststart = pastlog.index[len(todaylog.index)]
    reallast = todaylog.loc[realstop ,"SBPI"]
    castlast = pastlog.loc[realstop ,"SBPI"]
    adaptratio = (reallast+1)/(castlast+1) # no div by zero
    
    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last cast start is "{caststart}"')
    logger.info(f'Last real irridiance is "{reallast}"')
    logger.info(f'Last cast irridiance is "{castlast}"')
    logger.info(f'Last real/cast ratio is "{adaptratio}"')
    
    # The restlog needs adaptation
    restlog = pastlog.copy().loc[caststart:,:]
    restlog.loc[:,"SBPI"] *= adaptratio

    #Predict the samples
    await simulate_solix_1_power_w(
        restlog
    )

    #Ensure the plausibility of cast
    await simulate_solix_1_energy_wh(
        restlog, realsoc
    )
    
    #Join the current real data with the cast data
    castlog = pd.concat([todaylog,restlog])

    return today, castlog, realstop, caststart
