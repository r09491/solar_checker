__doc__=""" Estimates the irridiance of an Anker Solix 1 powerstation
system for the rest of today or a given castday dependend on the
averages of samples of some past days close to the prediction
day. Battery charging/discharging is predicted using a simulation with
the irridiance as input. Grid import/export is the median of the passed
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
    get_tunnel_logs
)
from brightsky import (
    Sky
)

EPS = 0.01      # 0.1, 0.01 ..
SCALE = 0.85    # 0.6, 0.75, 1.00
EXPONENT = 2.0  # 1.0, 2.0, 3.0
PERCENT = 0.01 
""" Returns a list of ratios to calculate power values from source
power values (adapted from formula by NASA) """
async def power_ratios(
        to: np.array, # 0 to 100
        frm: np.array, # 0 to 100
        exponent: float = EXPONENT,
        scale: float = SCALE,
        eps: float = EPS 
) -> np.array:
    return (((1.0-scale*( PERCENT*to )**exponent) + eps) /
            ((1.0-scale*( PERCENT*frm )**exponent) + eps))


SKY_TZ='Europe/Berlin'
""" Returns all sky data for each hour in the castday """
async def get_sky_pool_24h(
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


""" Return the power ratio of the sky in % for each hour from the
castday to today and the temeperatures of today """
async def get_sky_info_24h(
        castdays: List[str],
        lat: f64,
        lon: f64,
        tz: str = SKY_TZ
)  -> (List[pd.Dataframe], np.array, np.array, np.array):

    skytasks = [
        asyncio.create_task(
            get_sky_pool_24h(
                cd, lat, lon, tz
            )
        ) for cd in castdays]
    
    """ Get the list of associated columns """
    skys = await asyncio.gather(*skytasks)
    if skys is None:
        logger.warning(f'Unable to retrieve sky pools! Returning defaults')
        return 24*[100], 24*[100], 24*[100] 

    
    # The cast day the last in the list
    castdaysky = skys[-1].reset_index(drop=True) if skys[-1] is not None else None
    if castdaysky is None:
        logger.error(f'Unable to retrieve cast sky data! Returning defaults')
        return 24*[100], 24*[100], 24*[100] 

    # The covers of the castday
    castdaycover = castdaysky["cloud_cover"].values
    castdaycover = castdaycover[:min(len(castdaycover),24)]
    if len(castdaycover) != 24:  # Only 24h
        castdaycover = 24*[100]

    #The temperatures of castday
    temperatures = castdaysky["temperature"].values
    temperatures = temperatures[:min(len(temperatures),24)]
    if len(temperatures) != 24:  # Only 24h
        temperatures = 24*[15]
    
    # Based on the ratio of 'castdaycover' and 'tunneldaycover' the
    # power values of castday may be predicted by aopplying the
    # following formula if the average power day is given
        
    #     ratios = await power_ratios(
    #         castdaycover,
    #         tunneldaycover
    #     )

    # The weather is better (less clouds) with ratios >1. The weather
    # is worse (more clouds) with ratios <1

    tunnelcovers = None
    tunneldaycover = None
    if len(skys)>1:
        #The coverages of all the tunnel days
        tunnelcovers = [
            s["cloud_cover"].iloc[:-1] for s in skys[:-1] if s is not None
        ]
    
        # Calc the median of the tunnel days without castday
        _tunnelcovers = pd.concat(
            [c.reset_index(drop=True) for c in tunnelcovers]
        )
        tunneldaycover = _tunnelcovers.groupby(_tunnelcovers.index).mean()
        if len(tunneldaycover) != 24:  # Only 24h
            tunneldaycover = 24*[100]

    return (tunnelcovers,
            np.array(temperatures),
            np.array(tunneldaycover),
            np.array(castdaycover))


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


LOGTUNNELSIZE = 3
LOGDAYFORMAT="%y%m%d"
async def get_sample_logs_24h(
        logprefix: str,
        logdir: str,
        logwindow: int = LOGTUNNELSIZE
) -> (List, List[pd.DataFrame], pd.DataFrame, pd.DataFrame):

    # Get the logs close to the forecast day
    logdays, logs = await get_tunnel_logs(
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
    castday = logdays[-1]
    castdaylog = logs[-1]

    # Fix castdaylog
    await fix_sbpi_frozen(castdaylog) 
    await fix_sbpi_lazy(castdaylog)

    tunnellogs = None
    tunneldaylog = None
    if len(logs) > 1:
        # Remove logs without sun in the tunnel or missing entries
        tunnellogs = [
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
        if not tunnellogs:
            logger.error("No logs with irridiance in the tunnel")
            return [castday], None, None, castdaylog

        # Logs have irridiance
        
        logger.info(f'"{len(tunnellogs)}" tunnel days left after sun check.')

        # Get rid of frozrn SBPI samples
        for l in tunnellogs:
            await fix_sbpi_frozen(l) 
            await fix_sbpi_lazy(l)

        # Make the  single log from the many passed logs
    
        _tunnellogs = pd.concat(
            [l.reset_index(drop=True) for l in tunnellogs]
        )
        tunneldaylog = _tunnellogs.groupby(_tunnellogs.index).mean()   

        tunneldaylog.index = pd.date_range(
            castdaylog.index[0].date(),
            periods=len(tunneldaylog),
            freq="h"
        ).set_names('TIME')

        await fix_sbpi_lazy(tunneldaylog)

        # Fix logdays
        logdays = [
            l.index[0].strftime(LOGDAYFORMAT) for l in tunnellogs
        ] + [castday]
    
        logger.info(f'Cast finally based on "{len(logdays)-1}" days.')

    return logdays, tunnellogs, tunneldaylog, castdaylog


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
    iswarm = (log["T"] >T_WARM) if "T" in log else True
    
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

    issbpo = sbpo>0
    #ivp1[:] = 0.49*loss*(sbpo if sbpo.any() else sbpi)
    #ivp2[:] = 0.49*loss*(sbpo if sbpo.any() else sbpi)
    ivp1[issbpo] = 0.5*loss*sbpo[issbpo]
    ivp2[issbpo] = 0.5*loss*sbpo[issbpo]
    ivp1[~issbpo] = 0.5*loss*sbpi[~issbpo]
    ivp2[~issbpo] = 0.5*loss*sbpi[~issbpo]

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
        inv_ratio: f64 = 0.9,
        plug_ratio: f64 = 0.9,
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
        log, inv_ratio
    )

    #Update home plug power
    await simulate_home_plug_w(
        log, plug_ratio
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

    # Read the samples for today and the tunnel. Today is the castday.
    # The logs have hour resolution.
    days, _, tunneldaylog, todaylog = await get_sample_logs_24h(
        logprefix = logprefix,
        logdir = logdir
    )

    # today is the last list entry
    today = days[-1] if days is not None else None
    if today is None:
        logger.error(f'Irridiance not available for any day')
        return None, None, None, None

    # Read the temeratures of today, the cloud cover for the tunneldaylog
    # (average day) and today. Default values are returned for
    # detected errors.
    _, temperatures, tunneldaycover, todaycover = await get_sky_info_24h(
        days, lat, lon
    )

    # Calculate the ratios for the prediction. The tunnel sky factors
    # mulitplied with the today sky factor returns the today
    # irridiance.
    skyratios = await power_ratios(
        todaycover,
        tunneldaycover
    )

    # Add the temperatures to the frames
    todaylog.insert(
        todaylog.shape[1], "T", temperatures[:len(todaylog)]
    )

    # Abort if a cast is not possible (at the end of today)
    if len(todaylog) >= len(tunneldaylog):
        return today, todaylog, None, None

    # Abort if tunneldaylog is not 24h
    if len(tunneldaylog) <24:
        return today, todaylog, None, None
    
    tunneldaylog.insert(
        tunneldaylog.shape[1], "T", temperatures
    )
    
    # For the last hour not all samples aremeasured yet. Therefore the
    # last hour is part of the casting and excluded from the
    # calculating of the ratio.
    realstop = tunneldaylog.index[len(todaylog)-1]
    logger.info(f'Real stop at end of "{realstop}"')
    caststart = tunneldaylog.index[len(todaylog)]
    logger.info(f'Cast start at beginning of "{caststart}"')

    if not (("SBPI" in todaylog)):
        # No cast without real irridiance
        return today, tunneldaylog, realstop, caststart

    if not (("SBPI" in tunneldaylog)):
        # No cast without redicted irridiance
        return today, tunneldaylog, realstop, caststart

    # The sky cast starts with the tunneldaylog to be scaled with sky
    # factors for the whole day. 
    castlog = tunneldaylog
    castlog.loc[:, "SBPI"] *= skyratios

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[-1] if len(todaylog)>0 else None

    # Calc the real to cast ratio
    realsbpisum = todaylog.loc[:realstop,"SBPI"].sum()
    logger.info(f'Real irridiance is {realsbpisum:.0f} Wh')
    realsbpisum += castlog.loc[caststart:,"SBPI"].sum()
    logger.info(f'Expected irridiance is {realsbpisum:.0f} Wh')
    castsbpisum = castlog.loc[:,"SBPI"].sum()
    logger.info(f'Cast irridiance is {castsbpisum:.0f} Wh')
    realfactor = (
        (realsbpisum / castsbpisum) ** (1/ EXPONENT)
    ) if (
        realsbpisum >0 and castsbpisum >0
    ) else 1
    logger.info(f'REAL/CAST ratio is "{realfactor:.2f}"')

    # Adapt the rest of the log to the live factor
    restlog = castlog.loc[caststart:].copy() # Cast last hour of today
    restlog.loc[:,"SBPI"] *= realfactor

    realsbposum = todaylog.loc[:realstop, "SBPO"].sum()
    realivpsum = todaylog.loc[:realstop, ["IVP1","IVP2"]].sum().sum()
    realspphsum = todaylog.loc[:realstop, "SPPH"].sum()

    inv_ratio = min(1.0, (realivpsum+EPS)/(realsbposum+EPS))
    logger.info(f'IVP/SBPO ratio is "{inv_ratio:.2f}"')
    plug_ratio = min(1.0, realspphsum/(realivpsum+EPS))
    logger.info(f'SPPH/IVP ratio is "{plug_ratio:.2f}"')
    
    #Predict the system
    await simulate_system(
        restlog,
        realsoc,
        inv_ratio = inv_ratio, # Avoid div by zero
        plug_ratio = plug_ratio # Avoid div by zero
    )

    
    #Join the current real data with the cast data
    castlog = pd.concat([todaylog[:realstop],restlog])
    
    return today, castlog, realstop, caststart


""" Predicts the system for today with the provided cloud coverage
instead of the predicted cloud coverage """
async def predict_naive_custom(
        castday: str,
        cover: f64s,
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    # Read the 24 predicted samples for the model day. The later are
    # calculated from the window selected logs. The logs have hour
    # resolution. Today samples are ignored.
    days, _, tunneldaylog, _ = await get_sample_logs_24h(
        logprefix = logprefix,
        logdir = logdir
    )

    if days is None or tunneldaylog is None:
        logger.info(f'Nothing is in the tunnel')
        return None

    if len(tunneldaylog) < 24:
        logger.error(f'The provided tunnel log is illegal')
        return None

    today = days[-1]
    if castday is None:
        logger.info(f'Using {today} as castday')
        castday = today

    if castday < today:
        logger.error(f'"{castday}" cannot be in the past')
        return None

    # Read the temeratures, the cloud cover for the tunnel day (average
    # day) and today. Default values are returned for detected errors.
    _, temperatures, tunneldaycover, castdaycover = await get_sky_info_24h(
        days[:-1] + [castday], lat, lon
    )

    if cover is not None:
        logger.info(f'Using custom cloud coverage')
        castdaycover = cover

    # Calculate the ratios for prediction. The sky ratio
    # mulitplied with the today sky factor returns the today
    # irridiance.
    skyratios = await power_ratios(
        castdaycover,
        tunneldaycover
    )

    # Add the temperature column
    tunneldaylog.insert(tunneldaylog.shape[1], "T", temperatures)

    if (("SBPI" in tunneldaylog)):
    
        # Update the irridiance tunnel day average to expected aky
        # conditions
        tunneldaylog.loc[:,"SBPI"] *= skyratios

        # Keep SOC
        tunnelsoc = tunneldaylog["SBSB"].iloc[0]
            
        await simulate_system(
            tunneldaylog, tunnelsoc
        )

    return castday, tunneldaylog, None, tunneldaylog.index[0]


""" Returns the pure tunnelday as the average(median) of the days in the
tunnel without any scaling """
async def predict_naive_average(
        logprefix: str,
        logdir: str,
) -> (List, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    # Read the sampless for the average day. The logs have hour
    # resolution. Today samples are ignored.
    days, _, tunneldaylog, _ = await get_sample_logs_24h(
        logprefix = logprefix,
        logdir = logdir
    )

    if days is None or tunneldaylog is None:
        logger.info(f'Nothing is in the tunnel')
        return None

    if len(tunneldaylog) < 24:
        logger.error(f'The provided tunnel log is illegal')
        return None

    if not ("SBPI" in tunneldaylog):
        logger.error(f'The provided tunnel log has no sun power')
        return None
    
    # Keep SOC
    tunnelsoc = tunneldaylog["SBSB"].iloc[0]
            
    await simulate_system(
        tunneldaylog, tunnelsoc
    )

    return days[:-1], tunneldaylog, None, tunneldaylog.index[0]


""" Predict the system for the castday based on the sky information
only without any live data for days in the future """
async def predict_naive_castday(
        castday: str,
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    return await predict_naive_custom(
        castday = castday,
        cover = None,
        lat = lat,
        lon = lon,
        logprefix = logprefix,
        logdir = logdir)

""" Predict the system for today based in the provided coverage rather
than the forcast """
async def predict_naive_cover(
        cover: f64s,
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    return await predict_naive_custom(
        castday = None, #today
        cover = cover,
        lat = lat ,
        lon = lon,
        logprefix = logprefix,
        logdir = logdir)


""" Predict the system for today based on the blue coverage of the
clear sky """
async def predict_naive_blue(
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    return await predict_naive_custom(
        castday = None, #today
        cover = 24*[0.0],
        lat = lat,
        lon = lon,
        logprefix = logprefix,
        logdir = logdir)


""" Predict the system for today based on the dark coverage of the
completely cloud covered sky """
async def predict_naive_dark(
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
) -> (str, pd.DataFrame, pd.Timestamp, pd.Timestamp):

    return await predict_naive_custom(
        castday = None, #today
        cover = 24*[1.0],
        lat = lat,
        lon = lon,
        logprefix = logprefix,
        logdir = logdir)

    
""" FInd the best ratio parameter for the irridiance prediction """
async def predict_naive_configure(
        lat: f64,
        lon: f64,
        logprefix: str,
        logdir: str,
        exponents: List = np.linspace(2.0, 3.0, 4),
        scales: f64s = np.linspace(0.7, 1.2, 20),
        epss: f64s = np.linspace(0.01, 0.2, 20)
) -> (f64, f64, f64):

    # Read the 24h predicted samples for the model day. The later are
    # calculated from the window selected logs. The logs have hour
    # resolution. Today samples are ignored.
    days, tunnellogs, tunneldaylog, _ = await get_sample_logs_24h(
        logprefix = logprefix,
        logdir = logdir
    )

    if (days is None or
        tunnellogs is None or
        tunneldaylog is None):
        logger.info(f'Nothing is in the tunnel')
        return None

    if (not ("SBPI" in tunneldaylog)):
        logger.info(f'SBPI is not in the tunnelday log')
        return None

    testdaylog = tunnellogs[-1]
    if (not ("SBPI" in testdaylog)):
        logger.info(f'SBPI is not in the testday log')
        return None

    # Use dataframe for scaliing
    tunnel_sbpi= tunneldaylog.loc[:,"SBPI"]

    # Skip TIME
    test_sbpi= list(testdaylog.loc[:,"SBPI"].values)
    
    if (len(tunnel_sbpi) != 24 or
        len(test_sbpi) != 24):
        logger.error(f'The provided tunnel log is illegal')
        return None

    testday = days[-2]
    logger.info(f'Using {testday} as testday')

    # Read the temeratures, the cloud cover for the tunnel day (average
    # day) and today. Default values are returned for detected errors.
    tunnelcovers,  _, tunneldaycover, _ = await get_sky_info_24h(
        days, lat, lon
    )

    testdaycover = tunnelcovers[-1].values
    if ((testdaycover is None) or
        (tunneldaycover is None)):
        logger.info(f'No cloud coverage in weather')
        return None

    
    # Calculate the ratios for prediction. The sky ratio
    # mulitplied with the today sky factor returns the today
    # irridiance.

    best_error = None
    for exponent in exponents:
        for scale in scales:
            for eps in epss:
                skyratios = await power_ratios(
                    testdaycover,
                    tunneldaycover,
                    exponent,
                    scale,
                    eps
                )

                predict_sbpi= (tunnel_sbpi * skyratios).values
                #predict_sbpi /= np.max(predict_sbpi)
                #error = np.sqrt( (predict_sbpi - test_sbpi)**2) .sum()
                #print(predict_sbpi.sum())
                #print(tunnel_sbpi.sum())
                error = np.mean((tunnel_sbpi - predict_sbpi)**2)

                if (best_error is None) or (error < best_error):
                    best_exponent, best_scale, best_eps, best_error = exponent, scale, eps, error
                    #print(best_exponent, best_scale, best_eps, int(best_error))

    return best_exponent, best_scale, best_eps

