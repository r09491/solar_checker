__doc__=""" Estimates the irridiance of an Anker Solix 1 powerstation
system for the rest of today or a given castday dependend on the
averages of samples of some past days close to the prediction
day. Battery charging/discharging is predicted using a simulation with
the irridiance as input. Grid import/export is the mean of the passed
days. """

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
    List, Optional, f64, f64s
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

K = 1.2 # Ratio adaptor

async def skyadaptor(
        ratios: np.ndarray
) -> np.ndarray:
    return np.sqrt(ratios*K)


SKY_TZ='Europe/Berlin'
""" Returns the sky for each hour in the castday """
async def get_hour_sky_pool(
        castday: str,
        lat: float,
        lon: float,
        tz: str = SKY_TZ 
) -> Optional[pd.DataFrame]:
    
    sky = Sky(lat, lon, castday, tz)
    df = (await sky.get_solar_info()).iloc[:,1:].fillna(0.0)
    if df is None:
        logger.error(f'No sky features for {castday}')
        return None
    return df


""" Return the ratio of sky% for each hour from the
castday to today """
async def get_hour_sky_info(
        castdays: List[str],
        lat: f64,
        lon: f64,
        tz: str = SKY_TZ
)  -> (f64s,f64s):

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

    # Todays always the last in the list
    todaysky = skys[-1].reset_index(drop=True) if skys[-1] is not None else None
    if todaysky is None:
        logger.error(f'Unable to retrieve sky for "{castday}"')
        return None
    
    temperatures = todaysky["temperature"].values

    ratios = None
    if len(skys) >1:
        # Reduce past days
        pastskys = pd.concat(
            [s.reset_index(drop=True) for s in skys[:-1] if s is not None]
        )
        pastsky = pastskys.groupby(pastskys.index).mean()


        today_cloud_free = 100.0 - todaysky["cloud_cover"].values
        past_cloud_free = 100.0 - pastsky["cloud_cover"].values
        ratios = (today_cloud_free + 1) / (past_cloud_free + 1) # No div by zero!

        # The weather for today is better (more irridiance) with ratios > 1
        # The weather for today is worse (less irridiance) with ratios < 1
    
    return ratios[:-1] if ratios is not None else None, temperatures[:-1]


"""
Fix the inconsistencies of samples if solix is off (cold). There is
still may be irridiance. Then the inverter IVP1, IVP2 show it. Other
samples are simulated dependent on the irridiance SBPI.
"""
async def fix_sbpi(
        log: pd.DataFrame
):
    if not (
        ("SBPI" in log) and
        ("SBPB" in log) and
        (("IVP1" in log) or ("IVP2" in log))
    ):
        return # log not modified
    
    sbpi = log["SBPI"]
    sbpb = log["SBPB"]
    ivp = log["IVP1"] + log["IVP2"]
    isivpoversbpi = (ivp > sbpi) & ~(sbpb >0)
    log.loc[isivpoversbpi, "SBPI"] = ivp[isivpoversbpi]


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

    logger.info(f'Logs based on "len(logdays)" days.')

    # Make hour logs from the the minute logs
    logs = [l.set_index('TIME').resample(
        'h', label='left', closed='left'
    ).mean() for l in logs]

    # The forcastday is at the end of the list
    todaylog = logs[-1]

    # Make a single log from the many passed logs

    pastlog = None
    if len(logs)> 1:
        pastlogs = pd.concat(
            [l.reset_index(drop=True) for l in logs[:-1]]
        )
    
        pastlog = pastlogs.groupby(pastlogs.index).mean()

        pastlog.index = pd.date_range(
            todaylog.index[0].date(),
            periods=len(pastlog),
            freq="h"
        ).set_names('TIME')

        # Proper working Solix shall be ensured
        await fix_sbpi(pastlog)

    await fix_sbpi(todaylog)
    
    return logdays, pastlog, todaylog


async def get_predict_tables(
        casthours: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    if "IVP1" in casthours and "IVP2" in casthours:
        casthours["INV"] = casthours["IVP1"] + casthours["IVP2"] 
        casthours.drop("IVP1", inplace=True, axis=1)
        casthours.drop("IVP2", inplace=True, axis=1)

    if "SMP" in casthours:
        casthours[">SMP"] = casthours["SMP"]
        casthours.loc[casthours["SMP"]>0, ">SMP"]= 0
        casthours["SMP>"] = casthours["SMP"]
        casthours.loc[casthours["SMP"]<0,"SMP>"] = 0
        casthours.drop("SMP", inplace=True, axis=1)

    if "SBPB" in casthours:        
        casthours[">SBPB"] = casthours["SBPB"]
        casthours.loc[casthours["SBPB"]>0,">SBPB"] = 0
        casthours["SBPB>"] = casthours["SBPB"]
        casthours.loc[casthours["SBPB"]<0, "SBPB>"] = 0
        casthours.drop("SBPB", inplace=True, axis=1)

    casthours = casthours.resample(
        '3h', label='left', closed='left'
    ).mean()

    sbsb_df = None
    if "SBSB" in casthours:
        sbsb_df = casthours["SBSB"]
        sbsb_df.reset_index(inplace=True, drop=True)    
        casthours.drop("SBSB", inplace=True, axis=1)

    t_df = None
    if "T" in casthours:
        t_df = casthours["T"]
        t_df.reset_index(inplace=True, drop=True)    
        casthours.drop("T", inplace=True, axis=1)
    
    if "SPPH" in casthours and not casthours["SPPH"].any():
        casthours.drop("SPPH", inplace=True, axis=1)
    if ">SMP" in casthours and not casthours[">SMP"].any():
        casthours.drop(">SMP", inplace=True, axis=1)
    if ">SBPB" in casthours and not casthours[">SBPB"].any():
        casthours.drop(">SBPB", inplace=True, axis=1)
    if "SBPB>" in casthours and not casthours["SBPB>"].any():
        casthours.drop("SBPB>", inplace=True, axis=1)
    
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

    if t_df is not None:
        watts_table["T"] = t_df
    if sbsb_df is not None:
        energy_table["BAT%"] = 100*sbsb_df
    
    return (watts_table, energy_table)


"""
Simulates the Anker Solix generation 1 power part
"""
async def simulate_solix_1_power_w(
        log: pd.DataFrame
):

    sbpi = log["SBPI"]
    sbpb = log["SBPB"]
    sbpo = log["SBPO"]

    #Reset
    sbpb[:] = 0.0
    sbpo[:] = 0.0

    
    # No battery if cold
    iswarm = log["T"] >3

    # Avoid rounding errors
    isnosbpi = (sbpi <5) 
    sbpi[isnosbpi] = 0

    # Simultate low irradiance
    issbpi = (sbpi >0) & (sbpi <=35)
    sbpb[issbpi & iswarm] = -sbpi[issbpi & iswarm]
    
    # Simultate grey irradiance
    issbpi = (sbpi >35) & (sbpi <=100)
    sbpo[issbpi] = sbpi[issbpi]

    # constrain high irradiance
    issbpi = (sbpi > 800)
    sbpi[issbpi] = 800

    # Simultate grey irradiance
    issbpi = (sbpi >600)
    sbpb[issbpi & iswarm] = -600
    sbpo[issbpi] = sbpi[issbpi]-sbpb[issbpi]
    
    # Simultate bright irradiance
    issbpi = (sbpi >100) & (sbpi <=600)
    sbpb[issbpi & iswarm] = -sbpi[issbpi & iswarm] + 100
    sbpo[issbpi] = sbpi[issbpi] - sbpb[issbpi]


"""
Simulates the Anker Solix generation 1 energy part
"""
async def simulate_solix_1_energy_wh(
        log: pd.DataFrame,
        soc: f64,
        full_wh: f64 = -1600,
        empty_wh: f64 = -160
):

    if soc is None:
        return
    
    sbpi = log["SBPI"]
    sbpb = log["SBPB"]
    sbpo = log["SBPO"]

    # Avoid discharge below 100
    isnodischarge = (sbpb >0) & (sbpb<100)
    sbpb[isnodischarge] = 0
    sbpo[isnodischarge] = 0
    
    # Simulate battery almostfull
    log_wh = (sbpb.cumsum()+soc*full_wh)
    isprefull = (log_wh > full_wh) & (log_wh < 0.9*full_wh) & (log["SBPI"] >0) 
    sbpb[isprefull] = 0.05*full_wh
    sbpo[isprefull] = sbpi[isprefull] - 0.05*full_wh
    
    # Simulate battery full
    log_wh = (sbpb.cumsum()+soc*full_wh)
    isfull = log_wh <full_wh
    sbpb[isfull] = 0
    sbpo[isfull] = sbpi[isfull]

    # Simulate battery empty
    log_wh = (sbpb.cumsum()+soc*full_wh)
    isempty = log_wh >empty_wh
    sbpb[isempty] = 0
    sbpo[isempty] = 0
    
    
    # Update SOC
    log_wh = (sbpb.cumsum()+soc*full_wh)
    log["SBSB"] = log_wh/full_wh


"""
Simulates the inverter part
"""
async def simulate_inverter_w(
        log: pd.DataFrame,
        loss: f64
):
    sbpi = log["SBPI"]
    sbpo = log["SBPO"]
    ivp1 = log["IVP1"]
    ivp2 = log["IVP2"]

    ivp1[:] = 0.49*loss*(sbpo if sbpo.any() else sbpi)
    ivp2[:] = 0.49*loss*(sbpo if sbpo.any() else sbpi)

    #Otherwise keep IVP as is


    
"""
Simulates the home plug part
"""
async def simulate_home_plug_w(
        log: pd.DataFrame,
        loss: f64
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

    smp =  log["SMP"]
    isexport = smp <0
    smp[isexport] = 0
    
    # Vote for the balcony input
    
    balcony = log["SPPH"].copy()
    isbalcony = balcony >0

    ivp = log["IVP1"] + log["IVP2"]
    balcony[~isbalcony] = ivp[~isbalcony]
    isbalcony = balcony >0

    sbpo =  log["SBPO"]
    balcony[~isbalcony] = sbpo[~isbalcony]

    # Simultate the smartmeter
    smp[:] -= balcony
    

"""
Simulates the system
"""
async def simulate_system(
        log: pd.DataFrame,
        soc: f64,
        inv_loss: f64 = 0.9,
        plug_loss: f64 = 0.9,
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
        log, inv_loss
    )


    #Update home plug power
    await simulate_home_plug_w(
        log, plug_loss
    )

    #Update grid power
    await simulate_grid_w(
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

    # Read the samples for today and the mean of a number of past
    # days. The logs have hour resolution.
    days, pastlog, todaylog = await get_hour_sample_logs(
        logprefix = logprefix,
        logdir = logdir
    )

    # today is the last list entry
    today = days[-1]

    # Read the sky ratios from the pastlog to today. The sky ratio
    # mulitplied with the today sky factor returns the today
    # irridiance.
    skyratios, temperatures = await get_hour_sky_info(
        days, lat, lon
    )

    # Abort if skyratios are not avalable
    if skyratios is None:
        logger.error(f'Skyratios not available')
        return today, todaylog, None, None

    # Add the temperatures to the frames
    todaylog.insert(todaylog.shape[1], "T", temperatures[:len(todaylog)])

    # Abort if there is nothing in the past
    if pastlog is None:
        logger.error(f'There are no logs in the past')
        return today, todaylog, None, None
        
    # Abort if a cast is not possible (at the end of today)
    if len(todaylog) >= len(pastlog):
        return today, todaylog, None, None

    # Abort if pastlog is not 24h
    if len(pastlog) <24:
        return today, todaylog, None, None
    
    pastlog.insert(pastlog.shape[1], "T", temperatures)
    
    # For the last hour not all samples aremeasured yet. Therefore the
    # last hour is part of the casting and excluded from the
    # calculating of the ratio.
    realstop = pastlog.index[len(todaylog)-1]
    logger.info(f'Real stop at end of interval"{realstop}"')
    caststart = pastlog.index[len(todaylog)]
    logger.info(f'Cast start at beginning of interval"{caststart}"')

    if not (("SBPI" in todaylog)):
        # No cast without real irridiance
        return today, pastlog, realstop, caststart

    if not (("SBPI" in pastlog)):
        # No cast without redicted irridiance
        return today, pastlog, realstop, caststart


    # The sky cast starts with the pastlog to be scaled with sky
    # factors for the whole day. 
    castlog = pastlog
    skyfactor = await skyadaptor(skyratios)
    castlog.loc[:, "SBPI"] *= skyfactor


    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[-1] if len(todaylog)>0 else None

    # Calc the real to cast ratio
    
    realsbpi = todaylog.loc[:realstop,"SBPI"].iloc[-1]
    realsbpisum = realsbpi.sum()
    logger.info(f'Real irridiance is "{realsbpisum:.0f}"')

    castsbpi = castlog.loc[:realstop,"SBPI"].iloc[-1]
    castsbpisum = castsbpi.sum()
    logger.info(f'Cast irridiance is "{castsbpisum:.0f}"')
    
    realfactor = K*np.sqrt(realsbpisum/(castsbpisum+1)) # no div by zero
    logger.info(f'Real/Cast ratio is "{realfactor:.2f}"')

    # Adapt the rest of the log to the live factor

    restlog = castlog.loc[caststart:].copy() # Cast last hour of today 
    restlog.loc[:,"SBPI"] *= realfactor

    #Predict the system
    await simulate_system(
        restlog, realsoc
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

    if days is None or pastlog is None:
        logger.info(f'Nothing is in the past')
        return None

    today = days[-1]
    if castday < today:
        logger.error(f'"{castday}" is in the past')
        return None

    if len(pastlog) < 24:
        logger.error(f'The provided past log is illegal')
        return None


    # Read the sky ratios from the pastlog to the castday
    skyratios, temperatures = await get_hour_sky_info(
        days[:-1] + [castday], lat, lon
    )
    if skyratios is None:
        logger.error(f'Skyratios are not available')
        return None

    # Add the temperature column
    pastlog.insert(pastlog.shape[1], "T", temperatures)


    if (("SBPI" in pastlog)):
    
        # Update the irridiance past day average to expected aky
        # conditions
        skyfactor = await skyadaptor(skyratios)
        pastlog.loc[:,"SBPI"] *= skyfactor

        # Keep SOC
        pastsoc = pastlog["SBSB"].iloc[0]
            
        await simulate_system(
            pastlog, pastsoc
        )

    return castday, pastlog, None, pastlog.index[0]
