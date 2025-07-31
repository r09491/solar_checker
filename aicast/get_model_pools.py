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

from utils.samples import (
    get_columns_from_csv
)

from brightsky import (
    Sky
)

#import logging
#logging.disable(logging.CRITICAL)

""" """
async def get_sample_pool(
        logdir: str,
        logprefix: str,
        logday: str,
        logtz: str
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
            'day_of_year':t.day_of_year,
            'date':t.date.astype(str),
            'SBPI':sbpi,
            'SBPO':sbpo,
            'SMP':smp,
        }
    ).set_index('TIME')

    return df[~df.index.duplicated(keep='last')] 


""" """
async def get_daylight_pool(
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
    
    daylight_pool = (await get_daylight_pool(
        sky_pool.index, lat, lon
    ))['is_daylight']
    if daylight_pool is None:
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
    
    pools = [sample_pool, daylight_pool, sky_pool] 
    
    try:
        day_pool = pd.concat(pools, axis = 1)
    except pd.errors.InvalidIndexError:
        logger.error (f'Skipped pool for "{logday}"')
        return None
    
    day_pool = day_pool.dropna().tz_convert(tz).reset_index()
    logger.info (f'Have train pool for "{logday}"')
    return day_pool

""" """
def _get_logdays(logdir: str,
                 logprefix: str,
                 logdayformat: str = '*') -> List[str]:
    pattern = os.path.join(logdir, f'{logprefix}_{logdayformat}.log')
    logpaths = glob.glob(pattern)
    logfiles = [os.path.basename(lp) for lp in logpaths]
    lognames = [os.path.splitext(lf)[0] for lf in logfiles]
    logdays = [ln.replace(f'{logprefix}_', '') for ln in lognames]
    logdays.sort()
    return logdays


""" """
async def get_logdays(logdir: str,
                      logprefix: str,
                      logdayformat: str = '*') -> List[str]:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_logdays, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_logdays(**vars())


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
        logdir,
        logprefix,
        logdayformat
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
        pool = None
    return pool


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

    daylight_pool = (await get_daylight_pool(
        sky_pool.index, lat, lon
    ))['is_daylight']
    if daylight_pool is None:
        logger.error(f'No dayligh pool for "{day}"')
        return None

    t = sky_pool.index[:-1]
    sample_pool = pd.DataFrame(
        data = {
            'TIME':t,
            'hour':t.hour,
            'minute':t.minute,
            'day_of_year':t.day_of_year,
            'date':t.date.astype(str),
        }
    ).set_index('TIME')

    pools = [sample_pool, daylight_pool, sky_pool] 
    
    try:
        day_pool = pd.concat(pools, axis = 1)
    except pd.errors.InvalidIndexError:
        logger.error (f'Skipped pool for "{day}"')
        return None
    day_pool = day_pool.dropna().tz_convert(tz).reset_index()
    logger.info (f'Have predict pool for "{day}"')

    return day_pool.rename(columns={'index':'TIME'})
