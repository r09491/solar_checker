__doc__=""" Predicts the samples of an Anker Solix 1 powerbank for the
rest of today or a complete given castday assuming they behave similar
than some passed days. Changes for the rest of today are calculated
from ratio of the latest irridiance of today or suntime duration to
that of the passed days """

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

SUNSHINE_TZ='Europe/Berlin'
""" Returns the sunshine minutes for each hour in the castday """
async def get_hour_sunshine_pool(
        castday: str,
        lat: float,
        lon: float,
        tz: str = SUNSHINE_TZ 
) -> Optional[pd.DataFrame]:
    
    sky = Sky(lat, lon, castday, tz)
    df = (await sky.get_sky_info())['sunshine'].fillna(0.0)
    if df is None:
        logger.error(f'No sunshine features for {castday}')
        return None
    return df


""" Return the ratio of sunshine minutes for each hour from the
castday to today """
async def get_hour_sunshine_ratios(
        castdays: List[str],
        lat: f64,
        lon: f64,
        tz: str = SUNSHINE_TZ
)  -> Optional[np.ndarray]:

    suntasks = [asyncio.create_task(
        get_hour_sunshine_pool(
            cd, lat, lon, tz
        )
    ) for cd in castdays]
    
    """ Get the list of associated columns """
    suns = await asyncio.gather(*suntasks)
    if suns is None:
        logger.error(f'Unable to retrieve sunshine pools')
        return None

    # Reduce past days
    pastsuns = pd.concat(
        [s.reset_index(drop=True) for s in suns[:-1] if s is not None]
    )
    pastsun = pastsuns.groupby(pastsuns.index).mean()

    # Todays always the last in the list
    todaysun = suns[-1].reset_index(drop=True) if suns[-1] is not None else None
    if todaysun is None:
        logger.error(f'Unable to retrieve sunshine for "{castday}"')
        return None

    # No div by zero!
    ratios = (todaysun.values + 1) / (pastsun.values + 1) 
    return ratios[:-1]


LOGWINDOWSIZE = 2
async def get_hour_sample_logs(
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
    logs = [l.set_index('TIME').resample(
        'h', label='left', closed='left'
    ).mean() for l in logs]

    # The forcastday is at the end of the list
    todaylog = logs[-1]

    # Make a single log from the many passed logs
    
    pastlogs = pd.concat(
        [l.reset_index(drop=True) for l in logs[:-1]]
    )
    
    pastlog = pastlogs.groupby(pastlogs.index).mean()

    pastlog.index = pd.date_range(
        todaylog.index[0].date(),
        periods=len(pastlog),
        freq="h"
    ).set_names('TIME')

    return logdays, pastlog, todaylog


async def get_predict_tables(
        casthours: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    casthours = casthours.resample(
        '3h', label='left', closed='left'
    ).mean()

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
    issbpi = (log["SBPI"] > 880)
    log.loc[issbpi,"SBPI"] = 880

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >600)
    log.loc[issbpi,"SBPB"] = -600
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]-600

    # Simultate bright irradiance
    issbpi = (log["SBPI"] >100) & (log["SBPI"] <=600)
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

    # Avoid discharge below 100
    isnodischarge = (log["SBPB"] >0) & (log["SBPB"]<100)
    log.loc[isnodischarge,"SBPB"] = 0
    log.loc[isnodischarge,"SBPO"] = 0
    
    # Simulate battery almostfull
    log_wh = (log["SBPB"].cumsum()+realsoc*full_wh)
    isprefull = (log_wh > full_wh) & (log_wh < 0.9*full_wh)
    log.loc[isprefull,"SBPB"] = 0.1*full_wh
    log.loc[isprefull,"SBPO"] = log.loc[isprefull, "SBPI"] + 0.1*full_wh

    # Simulate battery full
    log_wh = (log["SBPB"].cumsum()+realsoc*full_wh)
    isfull = log_wh <full_wh
    log.loc[isfull,"SBPB"] = 0
    log.loc[isfull,"SBPO"] = log.loc[isfull, "SBPI"]

    # Simulate battery empty
    log_wh = (log["SBPB"].cumsum()+realsoc*full_wh)
    isempty = log_wh >empty_wh
    log.loc[isempty,"SBPB"] = 0
    log.loc[isempty,"SBPO"] = 0

    # Update SOC
    log_wh = (log["SBPB"].cumsum()+realsoc*full_wh)
    log["SBSB"] = log_wh/full_wh
    

"""
Simulates the grid power part
"""
async def simulate_grid_power_w(
        log: pd.DataFrame
):

    # Simultate the smartmeter
    log["SMP"] -= log["SBPO"]


@dataclass
class Script_Arguments:
    castday: str
    lat: f64
    lon: f64
    logprefix: str
    logdir: str

async def predict_naive_today(
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    # Read the available real samples for today and the 24 predicted
    # samples for the model day. The later are calculated from the
    # window selected logs. The logs have hour resolution.
    days, pastlog, todaylog = await get_hour_sample_logs(
        logprefix = logprefix,
        logdir = logdir
    )

    # today is the last list entry
    today = days[-1]

    # Abort if a cast is not possible (at the end of today)
    if len(todaylog.index) >= len(pastlog.index):
        # No cast is possible at the end of today
        return today, todaylog, None, None

    # Read the sun minute ratios from the pastlog to today
    sunratios = await get_hour_sunshine_ratios(
        days, lat, lon
    )
    if sunratios is None:
        logger.error(f'Sunratios not available')
        return None

    # Update the irridiance past day average to expected aky conditions
    pastlog_pre_sum = pastlog.loc[:,"SBPI"].sum()
    pastlog.loc[:,"SBPI"] *= sunratios 
    pastlog_post_sum = pastlog.loc[:,"SBPI"].sum()

    pastlog_perf = (pastlog_pre_sum / pastlog_post_sum)
    logger.info(f'Expected sun performance by weather: "{100*pastlog_perf:.0f}%"')
    
    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[-1]

    # Calc prediction data
    realstop = pastlog.index[len(todaylog.index)-1]
    caststart = pastlog.index[len(todaylog.index)]
    realsbpi = todaylog.loc[:realstop ,"SBPI"].sum()
    castsbpi = pastlog.loc[:realstop ,"SBPI"].sum()
    ratiosbpi = np.sqrt((realsbpi+1)/(castsbpi+1)) # no div by zero
        
    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last cast start is "{caststart}"')
    logger.info(f'Last real irridiance is "{realsbpi:.0f}"')
    logger.info(f'Last cast irridiance is "{castsbpi:.0f}"')
    logger.info(f'Last real/cast ratio is "{ratiosbpi:.2f}"')

    logger.info(f'Expected sun performance by observation: "{100*ratiosbpi:.0f}%"')
        
    # The restlog needs adaptation
    restlog = pastlog.loc[caststart:,:].copy()
    restlog.loc[:,"SBPI"] *= ratiosbpi
    
    #Predict the samples
    await simulate_solix_1_power_w(
        restlog
    )

    #Ensure the plausibility of cast
    await simulate_solix_1_energy_wh(
        restlog, realsoc
    )

    #Update grid power
    await simulate_grid_power_w(
        restlog
    )

    #Join the current real data with the cast data
    castlog = pd.concat([todaylog[:realstop],restlog])

    return today, castlog, realstop, caststart


""" Predict the radiation for the castday soley on the set of the pastdays """
async def predict_naive_castday(
        castday: str,
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    # Read the 24 predicted samples for the model day. The later are
    # calculated from the window selected logs. The logs have hour
    # resolution. Today samples are ignored.
    days, pastlog, _ = await get_hour_sample_logs(
        logprefix = logprefix,
        logdir = logdir
    )

    today = days[-1]
    if castday < today:
        logger.error(f'"{castday}" is in the past')
        return None
    

    # Read the sun minute ratios from the pastlog to the castday
    sunratios = await get_hour_sunshine_ratios(
        days[:-1] + [castday], lat, lon
    )
    if sunratios is None:
        logger.error(f'Sunratios are not available')
        return None

    sunperf = sunratios.mean()
    logger.info(f'Expected sun performance by forecast: "{100*sunperf:.0f}%"')

    pastsoc = pastlog["SBSB"].iloc[0]
    
    # Update the irridiance past day average to expected aky conditions
    pastlog.loc[:,"SBPI"] *= sunratios 

    #Predict the samples
    await simulate_solix_1_power_w(
        pastlog
    )

    #Ensure the plausibility of cast
    await simulate_solix_1_energy_wh(
        pastlog, pastsoc
    )

    #Update grid power
    await simulate_grid_power_w(
        pastlog
    )

    return castday, pastlog, None, pastlog.index[0]
