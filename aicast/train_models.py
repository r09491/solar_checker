__doc__=""" Train the models for the AI cast
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import sys
import os
import asyncio
import joblib

import pandas as pd
import numpy as np

try:
    import lightgbm as lgb
except OSError:
    logger.error(f'Unable to run on this system. Upgrade!')
    sys.exit(-99)
    
from sklearn.model_selection import (
    train_test_split
)
from sklearn.metrics import (
    mean_squared_error,
    r2_score
)

from utils.typing import (
    Optional, Any, Dict, List
)

from aicast.model_features import (
    SBPI_FEATURES,
    SBPI_FEATURES_lags,
    SBPI_FEATURES_rolls,
    SBSB_FEATURES,
    SBSB_FEATURES_lags,
    SBSB_FEATURES_rolls,
    SBPB_FEATURES,
    SBPB_FEATURES_lags,
    SBPB_FEATURES_rolls,
    SMP_FEATURES,
    SMP_FEATURES_lags,
    SMP_FEATURES_rolls,
)

from aicast.model_pools import (
    get_train_pools
)


async def get_model(
        X: pd.DataFrame, # for training
        y: pd.DataFrame  # for testing
) -> Any:

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, random_state=42,shuffle=False
    )

    # Negative value get higher weight tom compensate LGNM feature
    sample_weight = np.where(y_train<0, 2.0, 1.0)
    
    """
    model = lgb.LGBMRegressor(
        objective="regression",
        metric="rmse",
        boosting_type="gbdt",
        random_state=42,
        #n_estimators=125,
        #num_boost_round=2000,
        #early_stopping_round=50,
        learning_rate=0.05,
        #max_depth=64,
        num_leaves=63,         # increase to cover more dependencies 
        #min_data_in_leaf=128,   # increase to decrease overfitting
        #feature_fraction=0.9,   # decrease for more stabiliyt
        #bagging_fraction=0.8,  # decrease for more stabiliyt
        #bagging_freq =5,
        force_row_wise=True
    )
    """
    
    model = lgb.LGBMRegressor(
        objective="regression_l1",
        metric="mae",
        #objective="regression",
        #metric="rmse",
        boosting_type="gbdt",
        random_state=42,
        #n_estimators=500,
        n_estimators=1000,
        #num_boost_round=2000,
        #early_stopping_round=100,
        early_stopping_round=100,
        #learning_rate=0.05,
        learning_rate=0.02,
        max_depth=-1,
        num_leaves=63,         # increase to cover more dependencies 
        min_data_in_leaf=20,   # increase to decrease overfitting
        feature_fraction=0.5,   # decrease for more stabiliyt
        bagging_fraction=0.5,  # decrease for more stabiliyt
        bagging_freq=1,
        subsamples=0.9,
        colsample_bytree=0.9,
        lambda_l1=0.0,
        lambda_l2=0.0,
        force_row_wise=True,
        n_jobs=4,
        verbose=-1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        sample_weight=sample_weight
    )

    y_pred = model.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    logger.info(f'RMSE "{rmse:.2f}", R² Score "{r2:.3f}"')
    
    return model


"""  """
async def get_target_models(
        pool: pd.DataFrame,
        tgt_str: str,
        base_features: List,
        lag_periods: List = [],
        roll_periods: List = []
) -> Optional[Any]:

    if not (tgt_str in pool):
        logger.error(f'{tgt_str} is not in the train pool.')
        return None
    
    lags = [f'{tgt_str}_lag{l}' for l in lag_periods]
    rolls_mean = [f'{tgt_str}_roll{r}_mean' for r in roll_periods]
    rolls_std = [f'{tgt_str}_roll{r}_std' for r in roll_periods]

    lrt = lags+rolls_mean+rolls_std+[tgt_str]
    paras = [(t, lrt[:i]) for i, t in enumerate(lrt)]
    return [await get_model(
        X=pool[base_features + f], y=pool[t]
    ) for t, f in paras]


""" """
async def get_sbpi_models(pool: pd.DataFrame) -> Optional[Any]:
    logger.info(f'==================> SBPI model')

    return await get_target_models(
        pool = pool,
        tgt_str = "SBPI",
        base_features = SBPI_FEATURES,
        lag_periods = SBPI_FEATURES_lags,
        roll_periods = SBPI_FEATURES_rolls,
    )


""" """
async def get_sbsb_models(pool: pd.DataFrame) -> Optional[Any]:
    logger.info(f'==================> SBSB model')

    return await get_target_models(
        pool = pool,
        tgt_str = "SBSB",
        base_features = SBSB_FEATURES,
        lag_periods = SBSB_FEATURES_lags,
        roll_periods = SBSB_FEATURES_rolls,
    )


""" """
async def get_sbpb_models(pool: pd.DataFrame) -> Optional[Any]:
    logger.info(f'==================> SBPB model')

    return await get_target_models(
        pool = pool,
        tgt_str = "SBPB",
        base_features = SBPB_FEATURES,
        lag_periods = SBPB_FEATURES_lags,
        roll_periods = SBPB_FEATURES_rolls,
    )


""" """
async def get_smp_models(pool: pd.DataFrame) -> Optional[Any]:
    logger.info(f'==================> "SMP" models')

    return await get_target_models(
        pool = pool,
        tgt_str = "SMP",
        base_features = SMP_FEATURES,
        lag_periods = SMP_FEATURES_lags,
        roll_periods = SMP_FEATURES_rolls,
    )
    

""" """
async def get_models(pool: pd.DataFrame) -> Optional[Dict]:

    model_names = ["sbpi_models", "sbsb_models", "sbpb_models", "smp_models"]

    model_tasks = [
        asyncio.create_task(
            get_sbpi_models(pool)
        ),
        asyncio.create_task(
            get_sbsb_models(pool)
        ),
        asyncio.create_task(
            get_sbpb_models(pool)
        ),
        asyncio.create_task(
            get_smp_models(pool)
        )
    ]
    
    models = await asyncio.gather(*model_tasks)
    return dict(zip(model_names, models))


""" """
async def train_models(
        logdir: str,
        logprefix: str,
        logdayformat: str,
        tz: str,
        lat: float,
        lon: float
) -> int:

    pool = await get_train_pools(
        logdir, logprefix, logdayformat, tz, lat, lon
    )

    return (await get_models(pool)) if pool is not None else None
