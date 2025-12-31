__doc__=""" Predicts the samples of an Anker Solix 1 powerbank for the
rest of today or a complete given future castday assuming they behave
similar than some passed days. Changes for the rest of today are
calculated from ratio of the latest irridiance of today or cloud
coverage of the passed days """

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

SKY_TZ='Europe/Berlin'
""" Returns the sky for each hour in the castday """
async def get_hour_sky_pool(
        castday: str,
        lat: float,
        lon: float,
        tz: str = SKY_TZ 
) -> Optional[pd.DataFrame]:
    
    sky = Sky(lat, lon, castday, tz)
    df = (await sky.get_sky_info())['cloud_cover'].fillna(0.0)
    if df is None:
        logger.error(f'No sky features for {castday}')
        return None
    return df


""" Return the ratio of sky% for each hour from the
castday to today """
async def get_hour_sky_ratios(
        castdays: List[str],
        lat: f64,
        lon: f64,
        tz: str = SKY_TZ
)  -> Optional[np.ndarray]:

    skytasks = [asyncio.create_task(
        get_hour_sky_pool(
            cd, lat, lon, tz
        )
    ) for cd in castdays]
    
    """ Get the list of associated columns """
    skys = await asyncio.gather(*skytasks)
    if skys is None:
        logger.error(f'Unable to retrieve sky pools')
        return None

    # Reduce past days
    pastskys = pd.concat(
        [s.reset_index(drop=True) for s in skys[:-1] if s is not None]
    )
    pastsky = pastskys.groupby(pastskys.index).mean()

    # Todays always the last in the list
    todaysky = skys[-1].reset_index(drop=True) if skys[-1] is not None else None
    if todaysky is None:
        logger.error(f'Unable to retrieve sky for "{castday}"')
        return None

    # No div by zero!
    ratios = ((100 - todaysky.values) + 1) / ((100-pastsky.values) + 1) 
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
    #Reset
    log["SBPB"] = 0.0
    log["SBPO"] = 0.0
    
    # Avoid negative radiation
    isnosbpi = (log["SBPI"] <0) 
    log.loc[isnosbpi, "SBPI"] = 0
    
    # Simultate low irradiance
    issbpi = (log["SBPI"] >0) & (log["SBPI"] <=35) 
    log.loc[issbpi, "SBPB"] = -log.loc[issbpi, "SBPI"]
    #log.loc[issbpi, "SBPO"] = 0

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >35) & (log["SBPI"] <=100)
    #log.loc[issbpi,"SBPB"] = 0
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]

    # constrain high irradiance
    issbpi = (log["SBPI"] > 800)
    log.loc[issbpi,"SBPI"] = 800

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
        soc: f64,
        full_wh: f64 = -1600,
        empty_wh: f64 = -160
):

    # Avoid discharge below 100
    isnodischarge = (log["SBPB"] >0) & (log["SBPB"]<100)
    log.loc[isnodischarge,"SBPB"] = 0
    log.loc[isnodischarge,"SBPO"] = 0

    
    # Simulate battery almostfull
    log_wh = (log["SBPB"].cumsum()+soc*full_wh)
    isprefull = (log_wh > full_wh) & (log_wh < 0.9*full_wh) & (log["SBPI"] >0) 
    log.loc[isprefull,"SBPB"] = 0.05*full_wh
    log.loc[isprefull,"SBPO"] = log.loc[isprefull, "SBPI"] - 0.05*full_wh
    
    # Simulate battery full
    log_wh = (log["SBPB"].cumsum()+soc*full_wh)
    isfull = log_wh <full_wh
    log.loc[isfull,"SBPB"] = 0
    log.loc[isfull,"SBPO"] = log.loc[isfull, "SBPI"]


    # Simulate battery empty
    log_wh = (log["SBPB"].cumsum()+soc*full_wh)
    isempty = log_wh >empty_wh
    log.loc[isempty,"SBPB"] = 0
    log.loc[isempty,"SBPO"] = 0
    
    
    # Update SOC
    log_wh = (log["SBPB"].cumsum()+soc*full_wh)
    log["SBSB"] = log_wh/full_wh
    

"""
Simulates the grid power part
"""
async def simulate_grid_power_w(
        log: pd.DataFrame
):

    # Simultate the smartmeter
    log["SMP"] -= log["SBPO"]


"""
Simulates the system
"""
async def simulate_system(
        log: pd.DataFrame,
        soc: f64
):
    #Predict the samples
    await simulate_solix_1_power_w(
        log
    )

    #Ensure the plausibility of cast
    await simulate_solix_1_energy_wh(
        log, soc
    )

    #Update grid power
    await simulate_grid_power_w(
        log
    )
    

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

    # Read the sky ratios from the pastlog to today
    skyratios = await get_hour_sky_ratios(
        days, lat, lon
    )
    if skyratios is None:
        logger.error(f'Skyratios not available')
        return None
    
    # Update the irridiance past day average to expected aky conditions
    pastlog_pre_sum = pastlog.loc[:,"SBPI"].sum()
    pastlog.loc[:,"SBPI"] *= np.sqrt(skyratios)
    pastlog_post_sum = pastlog.loc[:,"SBPI"].sum()

    pastlog_perf = (pastlog_post_sum / pastlog_pre_sum)
    logger.info(f'Expected sky performance: "{100*pastlog_perf:.0f}%"')
    
    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[-1]

    # Calc prediction data. For the last hour not all samples
    # aremeasured yet. Therefore the last hour is part of the casting
    # and excluded from the calculating of the ratio.
    realstop = pastlog.index[len(todaylog.index)-1]
    caststart = pastlog.index[len(todaylog.index)]
    realsbpi = todaylog.loc[:realstop,"SBPI"]
    realsbpisum = realsbpi.iloc[:-1].sum()
    castsbpi = pastlog.loc[:realstop,"SBPI"]
    castsbpisum = castsbpi.iloc[:-1].sum()
    realsbpisum = realsbpisum if castsbpisum >0 else realsbpi.sum()
    castsbpisum = castsbpisum if castsbpisum >0 else castsbpi.sum()
    ratiosbpi = np.sqrt((realsbpisum+1)/(castsbpisum+1)) # no div by zero
    
    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last cast start is "{caststart}"')
    logger.info(f'Real irridiance is "{realsbpisum:.0f}"')
    logger.info(f'Cast irridiance is "{castsbpisum:.0f}"')
    logger.info(f'Real/Cast ratio is "{ratiosbpi:.2f}"')

    logger.info(f'Expected live performance: "{100*pastlog_perf*ratiosbpi:.0f}%"')
        
    # The restlog needs adaptation
    restlog = pastlog.loc[realstop:,:].copy()
    restlog.loc[:,"SBPI"] *= ratiosbpi

    #Predict the system
    await simulate_system(
        restlog, realsoc
    )

    #Join the current real data with the cast data
    castlog = pd.concat([todaylog[:realstop].iloc[:-1],restlog])

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
    

    # Read the sky ratios from the pastlog to the castday
    skyratios = await get_hour_sky_ratios(
        days[:-1] + [castday], lat, lon
    )
    if skyratios is None:
        logger.error(f'Skyratios are not available')
        return None

    # Update the irridiance past day average to expected aky conditions
    pastlog_pre_sum = pastlog.loc[:,"SBPI"].sum()
    pastlog.loc[:,"SBPI"] *= np.sqrt(skyratios) 
    pastlog_post_sum = pastlog.loc[:,"SBPI"].sum()
    pastlog_perf = (pastlog_post_sum / pastlog_pre_sum)
    logger.info(f'Expected sky performance by weather: "{100*pastlog_perf:.0f}%"')

    # Keep SOC
    pastsoc = pastlog["SBSB"].iloc[0]
            
    await simulate_system(
        pastlog, pastsoc
    )

    return castday, pastlog, None, pastlog.index[0]
