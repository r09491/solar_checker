import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import asyncio
import numpy as np
import pandas as pd
import joblib


from aicast.model_features import (
    SBPI_FEATURES,
    SBSB_FEATURES,
    SBPB_FEATURES,
    SMP_FEATURES
)

from aicast.get_model_pools import (
    get_predict_pool
)

async def predict_models(
    day: str,
    tz: str,
    lat: float,
    lon: float,
    modeldir: str,
) -> pd.DataFrame:

    try:
        sbpi_model = joblib.load(f'{modeldir}/lightgbm_sbpi_model.pkl')
        sbsb_model = joblib.load(f'{modeldir}/lightgbm_sbsb_model.pkl')
        sbpb_model = joblib.load(f'{modeldir}/lightgbm_sbpb_model.pkl')
        smp_model = joblib.load(f'{modeldir}/lightgbm_smp_model.pkl')
    except OSError:
        logger.error('Unable to run on this system. Upgrade!')
        return None
        
    # Get the basic pool for prediction
    try:
        pool = await get_predict_pool(
            day,
            tz,
            lat,
            lon
        )
    except:
        return None

    if pool is None or pool.empty:
        logger.error(f'Predict pool is empty for "{day}"')
        return None
    
    # Predict with models, sequence is mandatory
    pool['SBPI'] = sbpi_model.predict(pool[SBPI_FEATURES]).astype(int) 
    pool.loc[
        pool['SBPI']<0, 'SBPI'
    ] = 0
    pool.loc[
        pool['is_daylight']==0, 'SBPI'
    ] = 0


    pool['SBSB'] = sbsb_model.predict(pool[SBSB_FEATURES]).astype(int)
        
    pool['SBPB'] = sbpb_model.predict(pool[SBPB_FEATURES]).astype(int) 
    pool.loc[
        (pool['SBPI']>35) &
        (pool['SBPI']<100), 'SBPB'
    ] = 0
    pool.loc[
        (pool['SBPI']>0) &
        (pool['SBPB']>0), 'SBPB'
    ] = 0

    
    pool['SMP'] = smp_model.predict(pool[SMP_FEATURES]).astype(int)
    
    pool['SBPO'] = pool['SBPI'] + pool['SBPB']
    pool.loc[
        (pool['SBPI']>0) &
        (pool['SBPI']<=35), 'SBPO'
    ] = 0
    
    return pool.loc[:, ['TIME', 'SBPI', 'SBPB', 'SBPO', 'SMP']]
