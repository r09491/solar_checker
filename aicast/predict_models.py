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

from utils.typing import (
    Optional, Any, Dict, List
)

from aicast.model_features import (
    SBPI_FEATURES,
    SBPI_FEATURES_lags,
    SBPI_FEATURES_rolls,
    SBPB_FEATURES,
    SBPB_FEATURES_lags,
    SBPB_FEATURES_rolls,
    SMP_FEATURES,
    SMP_FEATURES_lags,
    SMP_FEATURES_rolls,
)

from aicast.model_pools import (
    get_predict_pool
)

""" Updates the pool with the results from the predictions """
async def predict_target_models(
        pool: pd.DataFrame, # in/out
        tgt_models: List,
        tgt_str: str,
        base_features: List,
        lag_periods: List = [],
        roll_periods: List = []
) -> Optional[None]:

    if (tgt_str in pool):
        logger.error(f'{tgt_str} is already in the predict pool.')
        return None
    
    lags = [f'{tgt_str}_lag{l}' for l in lag_periods]
    rolls = [f'{tgt_str}_roll{r}' for r in roll_periods]

    lrt = lags+rolls+[tgt_str]
    paras = [(t, lrt[:i]) for i, t in enumerate(lrt)]
    for (t,f), model in zip(paras, tgt_models):
        pool[t] = model.predict(pool[base_features + f])
        

""" Updates SBPI in the pool """
async def predict_sbpi_models(
        pool: pd.DataFrame, # in/out
        sbpi_models: List
) -> Optional[None]:

    await predict_target_models(
        pool = pool,
        tgt_models = sbpi_models,
        tgt_str = "SBPI",
        base_features = SBPI_FEATURES,
        lag_periods = SBPI_FEATURES_lags,
        roll_periods = SBPI_FEATURES_rolls
    )
    
    pool.loc[
        pool['SBPI']<0, 'SBPI'
    ] = 0
    pool.loc[
        pool['is_daylight']==0, 'SBPI'
    ] = 0

    
""" Updates SBPB in the pool """
async def predict_sbpb_models(
        pool: pd.DataFrame, # in/out
        sbpb_models: List
) -> Optional[None]:

    await predict_target_models(
        pool = pool,
        tgt_models = sbpb_models,
        tgt_str = "SBPB",
        base_features =SBPB_FEATURES,
        lag_periods = SBPB_FEATURES_lags,
        roll_periods = SBPB_FEATURES_rolls
    )

    pool.loc[
        (pool['SBPI']>35) &
        (pool['SBPI']<100), 'SBPB'
    ] = 0
    pool.loc[
        (pool['SBPI']>0) &
        (pool['SBPB']>0), 'SBPB'
    ] = 0


""" Updates SMP in the pool """    
async def predict_smp_models(
        pool: pd.DataFrame, # in/out
        smp_models: List
) -> Optional[None]:

    await predict_target_models(
        pool = pool,
        tgt_models = smp_models,
        tgt_str = "SMP",
        base_features = SMP_FEATURES,
        lag_periods = SMP_FEATURES_lags,
        roll_periods = SMP_FEATURES_rolls
    )

    
async def predict_models(
    day: str,
    tz: str,
    lat: float,
    lon: float,
    modeldir: str,
) -> pd.DataFrame:

    try:
        sbpi_models = joblib.load(f'{modeldir}/lightgbm_sbpi_models.pkl')
        sbpb_models = joblib.load(f'{modeldir}/lightgbm_sbpb_models.pkl')
        smp_models = joblib.load(f'{modeldir}/lightgbm_smp_models.pkl')            
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

    await predict_sbpi_models(
        pool = pool, sbpi_models = sbpi_models
    )
    
    # Predict SBPB
    await predict_sbpb_models(
        pool = pool, sbpb_models = sbpb_models
    )
    

    # Calculate SBPO
    
    pool['SBPO'] = pool['SBPI'] + pool['SBPB']
    pool.loc[
        (pool['SBPI']>0) &
        (pool['SBPI']<=35), 'SBPO'
    ] = 0

    
    # Predict SMP
    await predict_smp_models(
        pool = pool, smp_models = smp_models
    )

    return pool.loc[:, ['TIME', 'SBPI', 'SBPB', 'SBPO', 'SMP']]
