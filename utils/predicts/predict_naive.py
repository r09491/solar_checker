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
    POWER_NAMES,
    PARTITION_2_VIEW
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
        usecols = POWER_NAMES[:-4] # Skip plugs!
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

    sbsb_df = casthours["SBSB"]
    sbsb_df.reset_index(inplace=True, drop=True)    
    casthours.drop("SBSB", inplace=True, axis=1)
    
    casthours["INV"] = casthours["IVP1"] + casthours["IVP2"] 
    casthours.drop("IVP1", inplace=True, axis=1)
    casthours.drop("IVP2", inplace=True, axis=1)

    casthours[">SBPB"] = casthours["SBPB"]
    casthours[">SBPB"][casthours["SBPB"]>0] = 0
    casthours["SBPB>"] = casthours["SBPB"]
    casthours["SBPB>"][casthours["SBPB"]<0] = 0
    casthours.drop("SBPB", inplace=True, axis=1)

    casthours[">SMP"] = casthours["SMP"]
    casthours[">SMP"][casthours["SMP"]>0] = 0
    casthours["SMP>"] = casthours["SMP"]
    casthours["SMP>"][casthours["SMP"]<0] = 0
    casthours.drop("SMP", inplace=True, axis=1)

    if not casthours["SPPH"].any():
        casthours.drop("SPPH", inplace=True, axis=1)
    
    casthours.rename(columns=PARTITION_2_VIEW, inplace=True)

    starts = casthours.index.strftime("%H:00")
    stops = casthours.index.shift(1).strftime("%H:00")
    start_stop_df = pd.DataFrame({"START":starts, "STOP":stops})

    casthours.reset_index(inplace=True, drop=True)
    
    watts_table = pd.concat(
        [start_stop_df, casthours],
        axis=1
    )
    energy_table = pd.concat(
        [start_stop_df, 3*casthours.cumsum()],
        axis=1
    )

    energy_table["BAT%"] = 100*sbsb_df
    
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

    isivpover = (log["IVP1"] + log["IVP2"]) > log["SBPI"]
    
    # Simultate low irradiance
    issbpi = (log["SBPI"] >0) & (log["SBPI"] <=35) & (~isivpover) 
    log.loc[issbpi, "SBPB"] = -log.loc[issbpi, "SBPI"]
    #log.loc[issbpi, "SBPO"] = 0

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >35) & (log["SBPI"] <=100) & (~isivpover) 
    #log.loc[issbpi,"SBPB"] = 0
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]

    # constrain high irradiance
    issbpi = (log["SBPI"] > 800) & (~isivpover) 
    log.loc[issbpi,"SBPI"] = 800

    # Simultate grey irradiance
    issbpi = (log["SBPI"] >600) & (~isivpover) 
    log.loc[issbpi,"SBPB"] = -600
    log.loc[issbpi,"SBPO"] = log.loc[issbpi, "SBPI"]-600

    # Simultate bright irradiance
    issbpi = (log["SBPI"] >100) & (log["SBPI"] <=600) & (~isivpover) 
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
Simulates the inverter part
"""
async def simulate_inverter_w(
        log: pd.DataFrame,
        loss: f64 = 0.9
):

    sbpi = log["SBPI"]
    issbpi = sbpi >0    
    sbpo = log["SBPO"]
    issbpo = sbpo >0

    isbatcharge = issbpi & ~issbpo
    ivp = log.loc[isbatcharge,"IVP1"]
    ivp += log.loc[isbatcharge,"IVP2"]
    log.loc[isbatcharge,"SBPI"] = ivp

    isbatbypass = issbpi & issbpo
    log.loc[isbatbypass, "IVP1"] = 0.5*loss*sbpo[isbatbypass]
    log.loc[isbatbypass,"IVP2"] = 0.5*loss*sbpo[isbatbypass]

    #Otherwise keep IVP as is

    
"""
Simulates the home plug part
"""
async def simulate_home_plug_w(
        log: pd.DataFrame,
        loss: f64 = 0.9
):
    spph = log["SPPH"]
    isspph = spph >0
    if isspph.any():
        log.info("The home smart plug is present")

        # Keep samples not set in IVP!
        # Use simulated samples of IVP! 
        ivp = log["IVP1"] + log["IVP2"]
        isivp = ivp >0
        spph[isivp] = loss*ivp[isivp]

        
"""
Simulates the grid power part
"""
async def simulate_grid_w(
        log: pd.DataFrame
):

    # Vote for the balcony input
    
    balcony = log["SPPH"].copy()
    isbalcony = balcony >0

    ivp = log["IVP1"] + log["IVP2"]
    balcony[~isbalcony] = ivp[~isbalcony]
    isbalcony = balcony >0

    sbpo =  log["SBPO"]
    balcony[~isbalcony] = sbpo[~isbalcony]

    # Simultate the smartmeter
    log["SMP"] -= balcony
    

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
    
    #Update inverter power
    await simulate_inverter_w(
        log
    )

    #Update home plug power
    await simulate_home_plug_w(
        log
    )

    #Update grid power
    await simulate_grid_w(
        log
    )


"""
Fix the inconsistencies of samples introduced by resampling
"""
async def fix_todaylog(
        log: pd.DataFrame,
):
    sbpo = log["SBPO"]
    ivp = log["IVP1"] + log["IVP2"]
    isivpoversbpo = ivp > sbpo
    log.loc[isivpoversbpo, "SBPO"] = 0
    log.loc[isivpoversbpo, "SBPB"] = 0
    log.loc[isivpoversbpo, "SBPI"] = ivp[isivpoversbpo]
    

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

    await fix_todaylog(todaylog)
    
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

    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last cast start is "{caststart}"')

    #
    
    realsbpi = todaylog.loc[:realstop,"SBPI"]
    realsbpisum = realsbpi.iloc[:-1].sum()
    castsbpi = pastlog.loc[:realstop,"SBPI"]
    castsbpisum = castsbpi.iloc[:-1].sum()
    realsbpisum = realsbpisum if castsbpisum >0 else realsbpi.sum()
    castsbpisum = castsbpisum if castsbpisum >0 else castsbpi.sum()
    ratiosbpi = np.sqrt((realsbpisum+1)/(castsbpisum+1)) # no div by zero
    
    logger.info(f'Real irridiance is "{realsbpisum:.0f}"')
    logger.info(f'Cast irridiance is "{castsbpisum:.0f}"')
    logger.info(f'Real/Cast ratio is "{ratiosbpi:.2f}"')
    logger.info(f'Expected SBPI live performance: "{100*pastlog_perf*ratiosbpi:.0f}%"')

    #

    realivp1 = todaylog.loc[:realstop,"IVP1"]
    realivp1sum = realivp1.iloc[:-1].sum()
    castivp1 = pastlog.loc[:realstop,"IVP1"]
    castivp1sum = castivp1.iloc[:-1].sum()
    realivp1sum = realivp1sum if castivp1sum >0 else realivp1.sum()
    castivp1sum = castivp1sum if castivp1sum >0 else castivp1.sum()
    ratioivp1 = np.sqrt((realivp1sum+1)/(castivp1sum+1)) # no div by zero
    
    logger.info(f'Real irridiance is "{realivp1sum:.0f}"')
    logger.info(f'Cast irridiance is "{castivp1sum:.0f}"')
    logger.info(f'Real/Cast ratio is "{ratioivp1:.2f}"')
    logger.info(f'Expected IVP1 live performance: "{100*pastlog_perf*ratioivp1:.0f}%"')

    #
    
    realivp2 = todaylog.loc[:realstop,"IVP2"]
    realivp2sum = realivp2.iloc[:-1].sum()
    castivp2 = pastlog.loc[:realstop,"IVP2"]
    castivp2sum = castivp2.iloc[:-1].sum()
    realivp2sum = realivp2sum if castivp2sum >0 else realivp2.sum()
    castivp2sum = castivp2sum if castivp2sum >0 else castivp2.sum()
    ratioivp2 = np.sqrt((realivp2sum+1)/(castivp2sum+1)) # no div by zero
    
    logger.info(f'Real irridiance is "{realivp2sum:.0f}"')
    logger.info(f'Cast irridiance is "{castivp2sum:.0f}"')
    logger.info(f'Real/Cast ratio is "{ratioivp2:.2f}"')
    logger.info(f'Expected IVP2 live performance: "{100*pastlog_perf*ratioivp2:.0f}%"')

    #
    
    realspph = todaylog.loc[:realstop,"SPPH"]
    realspphsum = realspph.iloc[:-1].sum()
    castspph = pastlog.loc[:realstop,"SPPH"]
    castspphsum = castspph.iloc[:-1].sum()
    realspphsum = realspphsum if castspphsum >0 else realspph.sum()
    castspphsum = castspphsum if castspphsum >0 else castspph.sum()
    ratiospph = np.sqrt((realspphsum+1)/(castspphsum+1)) # no div by zero
    
    logger.info(f'Real irridiance is "{realspphsum:.0f}"')
    logger.info(f'Cast irridiance is "{castspphsum:.0f}"')
    logger.info(f'Real/Cast ratio is "{ratiospph:.2f}"')
    logger.info(f'Expected SPPH live performance: "{100*pastlog_perf*ratiospph:.0f}%"')

    
    # The restlog needs adaptation
    restlog = pastlog.loc[realstop:,:].copy()
    restlog.loc[:,"SBPI"] *= ratiosbpi
    restlog.loc[:,"IVP1"] *= ratioivp1
    restlog.loc[:,"IVP2"] *= ratioivp2
    restlog.loc[:,"SPPH"] *= ratiospph

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
