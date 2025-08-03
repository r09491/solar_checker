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
    SBPO_FEATURES,
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
        sbpo_model = joblib.load(f'{modeldir}/lightgbm_sbpo_model.pkl')
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
    pool['SMP'] = smp_model.predict(pool[SMP_FEATURES]).astype(int)
    pool['SBPO'] = sbpo_model.predict(pool[SBPO_FEATURES]).astype(int)

    # Plausibilit check to get rid of noise

    # Radiation cannot be negative
    sbpi_is_impossible = pool['SBPI']<0
    pool.loc[sbpi_is_impossible, 'SBPI'] = 0

    # Solix is chargin the battery below 35W and has no output
    sbpo_is_impossible = (0 < pool['SBPI']) & (pool['SBPI'] < 35)
    pool.loc[sbpo_is_impossible, 'SBPO'] = 0
    
    # Using system knowlegde
    pool['SBPB'] = pool['SBPO'] - pool['SBPI']

    return pool.loc[:, ['TIME', 'SBPI', 'SBPB', 'SBPO', 'SMP']]
