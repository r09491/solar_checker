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
    VIEW_NAMES,
    PARTITION_2_VIEW
)
from ..csvlog import(
    get_windowed_logs
)
from brightsky import (
    Sky
)

K = 1.1 # Ratio amplifier
KK = 50 # Ratio truncator

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
Fix the sample inconsistencies if the Solix is off (beloe zero
celsius). There still may be irridiance though. Then the sum of the
inverters IVP1, IVP2 is larger than SBPI (should be zero)
"""
async def fix_sbpi_lazy(
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
    sbpi[isivpoversbpi] = ivp[isivpoversbpi]

    
"""
Fix the inconsistencies if the Solix is not off but only returning
frozen values. The inverter values may still be good though. Then they
override the SBPI values.
"""
async def fix_sbpi_frozen(
        log: pd.DataFrame
):
    if not (
        ("SBPI" in log) and
        (("IVP1" in log) or ("IVP2" in log))
    ):
        return # log not modified

    ivp1 = log["IVP1"]
    ivp2 = log["IVP2"]
    sbpi = log["SBPI"]
    issbpion = sbpi>0
    sbpidiff = sbpi[issbpion].diff()
    sbpifreeze = sbpidiff[sbpidiff==0]
    if not sbpifreeze.all():
        logger.info("Solix has frozen: Replace all SBPI by IVP")
        sbpi[issbpion] = ivp1[issbpion] +ivp2[issbpion]

        
LOGWINDOWSIZE = 2
LOGDAYFORMAT="%y%m%d"
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

    logger.info(f'Cast initially based on "{len(logdays)}" days.')

    # Reample logs from minutes to hour resolution
    logs = [
        l.set_index('TIME').resample(
            'h', label='left', closed='left'
        ).mean() for l in logs
    ]

    # The day for the forcast is at the end of the list
    today = logdays[-1]
    todaylog = logs[-1]

    # Fix todaylog
    await fix_sbpi_frozen(todaylog) 
    await fix_sbpi_lazy(todaylog)

    
    # Remove logs without sun in the past or missing entries
    _pastlogs = [
        l for l in logs[:-1] if (
            len(l) == 24
        ) and (
            (
                'SBPI' in l and l['SBPI'].any()
            ) or (
                (
                    'IVP1' in l and l['IVP1'].any()
                ) and (
                    'IVP2' in l and l['IVP2'].any()
                )
            )
        )
    ]
    if not _pastlogs:
        logger.error("No logs with irridiance in the past")
        return [today], None, todaylog

    # Logs have irridiance

    logger.info(f'"{len(_pastlogs)}" past days left after sun check.')

    # Get rid of frozrn SBPI samples
    for l in _pastlogs:
        await fix_sbpi_frozen(l) 

    # Make the  single log from the many passed logs
    
    pastlogs = pd.concat(
        [l.reset_index(drop=True) for l in _pastlogs]
    )
    
    pastlog = pastlogs.groupby(pastlogs.index).mean()   

    pastlog.index = pd.date_range(
        todaylog.index[0].date(),
        periods=len(pastlog),
        freq="h"
    ).set_names('TIME')

    await fix_sbpi_lazy(pastlog)
    
    # Fix logdays
    logdays = [
        l.index[0].strftime(LOGDAYFORMAT) for l in _pastlogs
    ] + [today]
    
    logger.info(f'Cast finally based on "{len(logdays)-1}" days.')

    return logdays, pastlog, todaylog


async def get_predict_tables(
        casthours: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    c1h = casthours
    if "IVP1" in c1h and "IVP2" in c1h:
        c1h["INV"] = c1h["IVP1"] + c1h["IVP2"] 
        c1h.drop("IVP1", inplace=True, axis=1)
        c1h.drop("IVP2", inplace=True, axis=1)

    if "SMP" in c1h:
        c1h[">SMP"] = c1h["SMP"]
        c1h.loc[c1h["SMP"]>0, ">SMP"]= 0
        c1h["SMP>"] = c1h["SMP"]
        c1h.loc[c1h["SMP"]<0,"SMP>"] = 0
        c1h.drop("SMP", inplace=True, axis=1)

    if "SBPB" in c1h:        
        c1h[">SBPB"] = c1h["SBPB"]
        c1h.loc[c1h["SBPB"]>0,">SBPB"] = 0
        c1h["SBPB>"] = c1h["SBPB"]
        c1h.loc[c1h["SBPB"]<0, "SBPB>"] = 0
        c1h.drop("SBPB", inplace=True, axis=1)

    c3h = c1h.resample(
        '3h', label='left', closed='left'
    ).mean()

    sbsb_df = None
    if "SBSB" in c3h:
        sbsb_df = c3h["SBSB"]
        sbsb_df.reset_index(inplace=True, drop=True)    
        c3h.drop("SBSB", inplace=True, axis=1)

    t_df = None
    if "T" in c3h:
        t_df = c3h["T"]
        t_df.reset_index(inplace=True, drop=True)    
        c3h.drop("T", inplace=True, axis=1)

    if "SBPO" in c3h and not c3h["SBPO"].any():
        c3h.drop("SBPO", inplace=True, axis=1)        
    if "SPPH" in c3h and not c3h["SPPH"].any():
        c3h.drop("SPPH", inplace=True, axis=1)
    if ">SMP" in c3h and not c3h[">SMP"].any():
        c3h.drop(">SMP", inplace=True, axis=1)
    if ">SBPB" in c3h and not c3h[">SBPB"].any():
        c3h.drop(">SBPB", inplace=True, axis=1)
    if "SBPB>" in c3h and not c3h["SBPB>"].any():
        c3h.drop("SBPB>", inplace=True, axis=1)
    
    c3h.rename(columns=PARTITION_2_VIEW, inplace=True)
    c3h = pd.concat([c3h[c] for c in VIEW_NAMES if c in c3h.columns], axis=1)

    starts = c3h.index.strftime("%H:00")
    stops = c3h.index.shift(1).strftime("%H:00")
    start_stop_df = pd.DataFrame({"START":starts, "STOP":stops})
    c3h.reset_index(inplace=True, drop=True)
    
    watts_table = pd.concat(
        [start_stop_df, c3h],
        axis=1
    )
    energy_table = pd.concat(
        [start_stop_df, 3*c3h.cumsum()],
        axis=1
    )

    if t_df is not None:
        watts_table["T"] = t_df
    if sbsb_df is not None:
        energy_table["BAT%"] = 100*sbsb_df
    
    return (watts_table, energy_table)


T_WARM = 3

P_NOISE = 5
P_MIN = 0
P_LOW = 35
P_HIGH = 100
P_MAX = 880

"""
Simulates the ideal Anker Solix generation 1 power part
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

    
    # Avoid rounding errors
    isnosbpi = (sbpi <=P_NOISE) 
    sbpi[isnosbpi] = P_MIN

    # Constrain high irradiance
    issbpi = (sbpi > P_MAX)
    sbpi[issbpi] = P_MAX


    # No battery if cold
    iswarm = log["T"] >T_WARM
    
    # Simultate low irradiance
    issbpi = (sbpi >P_MIN) & (sbpi <=P_LOW)
    sbpb[issbpi & iswarm] = -sbpi[issbpi & iswarm]
    sbpo[issbpi & ~iswarm] = sbpi[issbpi & ~iswarm]
    
    # Simultate grey irradiance
    issbpi = (sbpi >P_LOW) & (sbpi <=P_HIGH)
    #sbpo[issbpi & iswarm] = sbpi[issbpi & iswarm]
    sbpo[issbpi] = sbpi[issbpi] # Bypass

    # Simultate blue irradiance
    issbpi = (sbpi >P_HIGH)
    sbpb[issbpi & iswarm] = -P_HIGH
    sbpo[issbpi & iswarm] = sbpi[issbpi & iswarm] - P_HIGH
    sbpo[issbpi & ~iswarm] = sbpi[issbpi & ~iswarm]
        
    # Simultate white irradiance
    issbpi = (sbpi >P_LOW) & (sbpi <=P_HIGH)
    sbpb[issbpi & iswarm] = -sbpi[issbpi & iswarm] + P_LOW
    sbpo[issbpi & iswarm] = sbpi[issbpi & iswarm] - P_LOW
    sbpo[issbpi & ~iswarm] = sbpi[issbpi & ~iswarm]

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

    ivp1[:] = 0.49*loss*sbpi #(sbpo if sbpo.any() else sbpi)
    ivp2[:] = 0.49*loss*sbpi #(sbpo if sbpo.any() else sbpi)

    #Otherwise keep IVP as is


    
"""
Simulates the home plug part
"""
async def simulate_home_plug_w(
        log: pd.DataFrame,
        loss: f64
):
    sbpi = log["SBPI"]
    spph = log["SPPH"]

    # Use simulated samples of IVP! 
    ivp = log["IVP1"] + log["IVP2"]
    spph[:] = loss*ivp # (ivp if ivp.any() else sbpi)

        
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
    today = days[-1] if days is not None else None
    if today is None:
        logger.error(f'Irridiance not available for any day')
        return None, None, None, None

    # Read the sky ratios from the pastlog to today. The sky ratio
    # mulitplied with the today sky factor returns the today
    # irridiance.
    skyratios, temperatures = await get_hour_sky_info(
        days, lat, lon
    )

    # Abort if skyratios are not avalable
    if skyratios is None:
        logger.error(f'Skyratios not available')
        return None, None, None, None

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
    logger.info(f'Real stop at end of "{realstop}"')
    caststart = pastlog.index[len(todaylog)]
    logger.info(f'Cast start at beginning of "{caststart}"')

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

    # No div by zero, produces "1" for small values!
    realfactor = K*np.sqrt((realsbpisum//KK+0.01)/(castsbpisum//KK+0.01))
    logger.info(f'Real/Cast ratio is "{realfactor:.2f}"')

    # Adapt the rest of the log to the live factor

    restlog = castlog.loc[caststart:].copy() # Cast last hour of today
    restlog.loc[:,"SBPI"] *= realfactor

    realsbpo = todaylog.loc[:realstop, "SBPO"].iloc[-1]
    realsbposum = realsbpo.sum()
    logger.info(f'Real bank watts is "{realsbposum:.0f}"')
    
    realivp = todaylog.loc[:realstop, ["IVP1","IVP2"]].iloc[-1]
    realivpsum = realivp.sum().sum()
    logger.info(f'Real inverter watts is "{realivpsum:.0f}"')

    realspph = todaylog.loc[:realstop, "SPPH"].iloc[-1]
    realspphsum = realspph.sum()
    logger.info(f'Real plug watts is "{realspphsum:.0f}"')

    # If addapted the losses maybe > 1 before simulation
    inv_loss = min(1.0, (realivpsum+0.01)/(realsbposum+0.01))
    plug_loss = min(1.0, realspphsum/(realivpsum+0.01))
    
    #Predict the system
    await simulate_system(
        restlog, realsoc,
        inv_loss = inv_loss, # Avoid div by zero
        plug_loss = plug_loss # Avoid div by zero
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
