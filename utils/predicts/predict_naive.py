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

from datetime import(
    datetime
)
from ..typing import(
    List, Optional, f64
)
from ..common import(
    PREDICT_POWER_NAMES
)
from ..csvlog import(
    get_windowed_logs
)
from brightsky import (
    Sky
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
    castday: str
    lat: f64
    lon: f64
    logprefix: str
    logdir: str

async def predict_naive_today(
        logprefix: str,
        logdir: str
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    today, pastlog, todaylog = await get_hour_logs(
        logprefix = logprefix,
        logdir = logdir
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


SUNSHINE_TZ='Europe/Berlin'

"""
Returns the sunshine minute for each hour in the castday
"""
async def get_sunshine_pool(
        castday: str,
        lat: float,
        lon: float,
        tz: str = SUNSHINE_TZ 
) -> Optional[pd.DataFrame]:
    
    sky = Sky(lat, lon, castday, tz)
    df = (await sky.get_sky_info())['sunshine']
    if df is None:
        logger.error(f'No sky features for {castday}')
        return None
    if df.isnull().any().any():
        logger.error(f'At least one undefined column for {castday}')
        return None

    return df


""" Return the ratio of sunshine minutes for each hour from the
castday to today """
async def get_sunshine_ratios(
        castdays: List[str],
        lat: f64,
        lon: f64,
        tz: str = SUNSHINE_TZ
)  -> Optional[np.ndarray]:

    if len(castdays) >2:
        logger.error(f'Only two castdays allowed')
        return None

    if castdays[-1] >= castdays[0]:
        logger.error(f'Castday to be in the future')
        return None

    pooltasks = [asyncio.create_task(
        get_sunshine_pool(
            cd, lat, lon, tz
        )
    ) for cd in castdays]
    
    """ Get the list of associated columns """
    pools = await asyncio.gather(*pooltasks)
    if pools is None:
        logger.error(f'Unable to retrieve sunshine pools')
        return None

    # No div by zero!
    ratios = (pools[0].values + 1) / (pools[-1].values + 1)
    
    return ratios[:-1]


""" """
async def predict_naive_castday(
        castday: str,
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    cast = await predict_naive_today(
        logprefix,
        logdir
    )
    if cast is None:
        logger.error(f'Today Hour Predict failed')
        return None

    today, casthours, realstop, caststart = cast

    if castday <= today:
        logger.error(f'Predict day is in the past')
        return None

    
    sunratios = await get_sunshine_ratios(
        [castday, today], lat, lon
    )
    if sunratios is None:
        logger.error(f'Sunratios not available')
        return None

    
    # Keep SOC
    castsoc = casthours.iloc[0]["SBSB"]

    casthours.index = pd.date_range(
        datetime.strptime(castday, "%y%m%d"),
        periods=24,
        freq="h"
    )

    #Cast radiation
    casthours.loc[:, "SBPI"] *= sunratios

    #Predict the samples
    await simulate_solix_1_power_w(
        casthours
    )

    #Ensure the plausibility of cast
    await simulate_solix_1_energy_wh(
        casthours, castsoc
    )

    return castday, casthours, None, casthours.index[0]
