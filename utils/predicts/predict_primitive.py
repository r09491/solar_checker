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
    List, Optional
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

    starts = casthours.index.strftime("%H:00")
    stops = casthours.index.strftime("%H:59")
    start_stop_df = pd.DataFrame({"START":starts, "STOP":stops})

    sbsb_df = casthours["SBSB"]
    sbsb_df.reset_index(inplace=True, drop=True)
    
    casthours.drop("SBSB", inplace=True, axis=1)
    casthours.reset_index(inplace=True, drop=True)
    
    watts_table = pd.concat([start_stop_df, casthours], axis=1)
    energy_table = pd.concat([start_stop_df, casthours.cumsum(), 100*sbsb_df], axis=1)
    
    return (watts_table, energy_table)


@dataclass
class Script_Arguments:
    logprefix: str
    logdir: str

async def predict_primitive(
        args: Script_Arguments
) -> (pd.DataFrame, pd.Timestamp, pd.Timestamp):
    
    days = await get_logdays(
        logprefix = args.logprefix,
        logdir = args.logdir
    )
    if days is None:
        logger.error("Failed to get logdays")
        return None

    yesterday, today = days[-2:]
    logger.info(f'Predicting "{today}" using "{yesterday}"')

    yesterday, todaylog = await asyncio.gather(
        get_hour_log(
            logday = yesterday,
            logprefix = args.logprefix,
            logdir = args.logdir
        ),
        get_hour_log(
            logday = today,
            logprefix = args.logprefix,
            logdir = args.logdir
        )
    )

    # Adapt the cast indices
    yesterday.index = pd.date_range(
        todaylog.index[0].date(),
        periods=24,
        freq="h"
    )

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[0]
    
    # Calc prediction data
    realstop = yesterday.index[len(todaylog.index)-1]
    caststart = yesterday.index[len(todaylog.index)]
    reallast = todaylog.loc[realstop ,"SBPI"]
    castlast = yesterday.loc[realstop ,"SBPI"]
    adaptratio = reallast/castlast if castlast >0.0 else 0.0

    logger.info(f'Last real irridiance is "{reallast}"')
    logger.info(f'Last cast irridiance is "{castlast}"')
    logger.info(f'Last real/cast ratio is "{adaptratio}"')
    logger.info(f'Last cast start is "{caststart}"')
    
    # The restlog needs adaptation
    restlog = yesterday.copy().loc[caststart:,:]
    if adaptratio >0.0:
        """ Try the cast with latest ratio """
        # Cast irridiance by scalling using last hour
        restlog["SBPI"] *= adaptratio

        # Simultate low irradiance
        issbpi = restlog["SBPI"] <35 
        restlog.loc[issbpi, "SBPB"] = -restlog.loc[issbpi, "SBPI"]
        restlog.loc[issbpi, "SBPO"] = 0

        # Simultate grey irradiance
        issbpi = (restlog["SBPI"] >=35) & (restlog["SBPI"] <100)
        restlog.loc[issbpi,"SBPB"] = 0
        restlog.loc[issbpi,"SBPO"] = restlog.loc[issbpi, "SBPI"]

        # Simultate bright irradiance
        issbpi = (restlog["SBPI"] >=100) & (restlog["SBPI"] <800)
        restlog.loc[issbpi,"SBPB"] = -restlog.loc[issbpi,"SBPI"] + 100
        restlog.loc[issbpi,"SBPO"] = 100

        # Simultate high irradiance
        issbpi = (restlog["SBPI"] >=800)
        restlog.loc[issbpi,"SBPB"] = -600
        restlog.loc[issbpi,"SBPO"] =  restlog.loc[issbpi,"SBPI"] - 600

    #Best cast is real data
    castlog = pd.concat([todaylog,restlog])

    # Simulate battery full
    isfull = castlog["SBPB"].cumsum() <-1600
    castlog.loc[isfull,"SBPB"] = 0
    castlog.loc[isfull,"SBPO"] = castlog.loc[isfull, "SBPI"]

    # Simulate battery empty
    isempty = castlog["SBPB"].cumsum() >0
    castlog.loc[isempty,"SBPB"] = 0
    castlog.loc[isempty,"SBPO"] = 0
    
    castlog["SBSB"] = realsoc - castlog["SBPB"].cumsum()/1600

    return castlog, realstop, caststart
