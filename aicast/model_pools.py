__doc__=""" Collects the data for the AI cast
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import sys, os, glob, asyncio
from os.path import basename

import pandas as pd
import numpy as np

from pvlib.solarposition import (
    get_solarposition
)

from utils.typing import (
    Optional, Any, Dict, List
)

from utils.csvlog import (
    get_logdays
)

from utils.samples import (
    get_columns_from_csv
)

from brightsky import (
    Sky
)

from aicast.model_features import (
    SBPI_FEATURES_lags,
    SBPI_FEATURES_rolls,
    SBPB_FEATURES_lags,
    SBPB_FEATURES_rolls,
    SMP_FEATURES_lags,
    SMP_FEATURES_rolls,
)

#import logging
#logging.disable(logging.CRITICAL)

""" """
async def get_sample_pool(
        logdir: str,
        logprefix: str,
        logday: str,
        logtz: str,
        full_wh: float = -1600
) -> Optional[pd.DataFrame]:

    cols = await get_columns_from_csv(
        logday, logprefix, logdir
    )
    if cols is None:
        logger.error(f'No samples for {logday}')
        return None
    
    sbpi = cols['SBPI']
    if sbpi is None:
        logger.error(f'No SBPI samples for {logday}')
        return None
        
    sbpb = cols['SBPB']
    if sbpb is None:
        logger.error(f'No SBPB samples for {logday}')
        return None

    sbpo = cols['SBPO']
    if sbpo is None:
        logger.error(f'No SBPO samples for {logday}')
        return None
    
    smp = cols['SMP']
    if smp is None:
        logger.error(f'No SMP samples for {logday}')
        return None

    t = cols['TIME']
    if t is None:
        logger.error(f'No TIME samples für {logday}')
        return None
        
    t = pd.DatetimeIndex(t).tz_localize(logtz, ambiguous = 'NaT')

    df = pd.DataFrame(
        data = {
            'TIME':t,
            'hour':t.hour,
            'minute':t.minute,
            'month':t.month,
            'year':t.year,
            'day_of_year':t.day_of_year,
            'date':t.date.astype(str),
            'SBPI':sbpi,
            'SBPB':sbpb,
            'SBPO':sbpo,
            'SMP':smp,
        }
    ).set_index('TIME')
    
    return df[~df.index.duplicated(keep='last')]


""" """
async def get_position_pool(
        time: pd.DatetimeIndex,
        lat: float,
        lon: float,
) -> Optional[pd.DataFrame]:
    
    sunpos = get_solarposition(time, lat, lon)

    sunpos['is_daylight'] = (
        sunpos['elevation'] > 0
    ).astype(int) if (
        sunpos is not None
    ) else None

    sunpos['can_see_sun'] = (
        (sunpos['azimuth'] > 95) &
        (sunpos['azimuth'] < 275)
    ).astype(int) if (
        sunpos is not None
    ) else None

    return sunpos


""" """
async def get_sky_pool(
        logday: str,
        tz: str,
        lat: float,
        lon: float
) -> Optional[pd.DataFrame]:
    
    sky = Sky(lat,lon, logday, tz)
    df = await sky.get_ai_feature_info()
    if df is None:
        logger.error(f'No sky features for {logday}')
        return None
    if df.isnull().any().any():
        logger.error(f'At least one undefined column for {logday}')
        return None
        
    try:
        df.index = pd.DatetimeIndex(df.index).tz_convert(tz)
    except TypeError:
        # May be switching from summer time to winter time
        logger.error(f'Skipped sky features for "{logday}"')
        return None
    
    df = df.resample("1min").interpolate()
    return df


""" """
async def get_train_pool(
        logdir: str,
        logprefix: str,
        logday: str,
        tz: str,
        lat: float,
        lon: float
) -> Optional[pd.DataFrame]:

    sky_pool = await get_sky_pool(
        logday, tz, lat, lon
    )
    if sky_pool is None:
        logger.error(f'No sky pool for "{logday}"')
        return None
    logger.info(f'Have sky pool for "{logday}"')
    
    position_pool = (await get_position_pool(
        sky_pool.index, lat, lon
    ))  ##['is_daylight']
    if position_pool is None:
        logger.error(f'No dayligh pool for "{logday}"')
        return None
    logger.info(f'Have daylight pool for "{logday}"')

    sample_pool = await get_sample_pool(
        logdir, logprefix,logday,tz
    )
    if sample_pool is None:
        logger.error(f'No sample pool for "{logday}"')
        return None
    logger.info(f'Have sample pool for "{logday}"')
    
    pools = [sample_pool, position_pool, sky_pool] 
    
    try:
        day_pool = pd.concat(pools, axis = 1)
    except pd.errors.InvalidIndexError:
        logger.error (f'Skipped pool for "{logday}"')
        return None

    day_pool = day_pool.dropna().tz_convert(tz).resample('1min').bfill()
    logger.info (f'Have day pool for "{logday}"')

    return day_pool


""" """
async def get_train_pools(
        logdir: str,
        logprefix: str,
        logdayformat: str,
        tz: str,
        lat: str,
        lon: str
) -> Optional[pd.DataFrame]:

    """ Get the list of logdays """
    logdays = (await get_logdays(
        logdir=logdir,
        logprefix=logprefix,
        logdayformat=logdayformat
    ))

    pool_tasks = [
        asyncio.create_task(
            get_train_pool(
                logdir,logprefix,ld,tz,lat,lon
            )
        ) for ld in logdays]
    
    """ Get the list of associated columns """
    pool_frames = await asyncio.gather(*pool_tasks)

    try:
        pool = pd.concat(pool_frames)
    except ValueError:
        logger.error('Unable to create training pools')
        return None

    #Extend the SMP base features for time series
    for lag in SBPI_FEATURES_lags:
        pool[f'SBPI_lag{lag}'] = pool['SBPI'].shift(lag)
    for roll in SBPI_FEATURES_rolls:
        pool[f'SBPI_roll{roll}'] = pool['SBPI'].shift(roll)

    #Extend the SBPB base features for time series
    for lag in SBPB_FEATURES_lags:
        pool[f'SBPB_lag{lag}'] = pool['SBPB'].shift(lag)
    for roll in SBPB_FEATURES_rolls:
        pool[f'SBPB_roll{roll}'] = pool['SBPB'].shift(roll)
        
    #Extend the SMP base features for time series
    for lag in SMP_FEATURES_lags:
        pool[f'SMP_lag{lag}'] = pool['SMP'].shift(lag)
    for roll in SMP_FEATURES_rolls:
        pool[f'SMP_roll{roll}'] = pool['SMP'].shift(roll)

    return pool.dropna() # With above value the oldest 20 Min are dropped!


""" """
async def get_predict_pool(
        day: str,
        tz: str,
        lat: float,
        lon: float
) -> Optional[pd.DataFrame]:

    sky_pool = await get_sky_pool(
        day, tz, lat, lon
    )
    if sky_pool is None:
        logger.error(f'No sky pool for "{day}"')
        return None
    
    position_pool = (await get_position_pool(
        sky_pool.index, lat, lon
    ))
    if position_pool is None:
        logger.error(f'No dayligh pool for "{day}"')
        return None
    
    t = sky_pool.index[:-1]
    sample_pool = pd.DataFrame(
        data = {
            'TIME':t,
            'hour':t.hour,
            'minute':t.minute,
            'month':t.month,
            'year':t.year,
            'day_of_year':t.day_of_year,
            'date':t.date.astype(str),
        }
    ).set_index('TIME')

    pools = [sample_pool, position_pool, sky_pool] 
    
    try:
        day_pool = pd.concat(pools, axis = 1)
    except pd.errors.InvalidIndexError:
        logger.error (f'Skipped pool for "{day}"')
        return None

    day_pool = day_pool.dropna().tz_convert(tz).reset_index()
    logger.info (f'Have predict pool for "{day}" with "{len(day_pool)}" entries.')

    return day_pool.rename(columns={'index':'TIME'})
