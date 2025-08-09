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
    SBPB_FEATURES,
    SMP_roll5_FEATURES,
    SMP_roll17_FEATURES,
    SMP_FEATURES
)

from aicast.get_model_pools import (
    get_train_pools
)


async def get_model(
        X: pd.DataFrame, # for training
        y: pd.DataFrame  # for testing
) -> Any:

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = lgb.LGBMRegressor(
        n_estimators=125,
        learning_rate=0.05,
        force_row_wise=True
    )
    model.fit(
        X_train, y_train, eval_set=[(X_val, y_val)]
    )

    y_pred = model.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    logger.info(f'RMSE "{rmse:.2f}"')
    logger.info(f'R² Score "{r2:.3f}"')
    
    return model


async def get_sbpi_model(pools: pd.DataFrame) -> Optional[Any]:

    logger.info(f'"SBPI" model')
    model = await get_model(X=pools[SBPI_FEATURES], y=pools['SBPI'])
    return model

async def get_sbpb_model(pools: pd.DataFrame) -> Optional[Any]:

    logger.info(f'"SBPB" model')
    model = await get_model(X=pools[SBPB_FEATURES], y=pools['SBPB'])
    return model

async def get_smp_roll5_model(pools: pd.DataFrame) -> Optional[Any]:

    logger.info(f'"SMP_roll5" model')
    model = await get_model(X=pools[SMP_roll5_FEATURES], y=pools['SMP_roll5'])
    return model

async def get_smp_roll17_model(pools: pd.DataFrame) -> Optional[Any]:

    logger.info(f'"SMP_roll17" model')
    model = await get_model(X=pools[SMP_roll17_FEATURES], y=pools['SMP_roll17'])
    return model

async def get_smp_model(pools: pd.DataFrame) -> Optional[Any]:

    logger.info(f'"SMP" model')
    model = await get_model(X=pools[SMP_FEATURES], y=pools['SMP'])
    return model

async def get_models(pools: pd.DataFrame) -> Optional[Any]:

    model_names = ["sbpi_model",
                   "sbpb_model",
                   "smp_roll5_model",
                   "smp_roll17_model",
                   "smp_model"
                   ]

    model_tasks = [
        asyncio.create_task(
            get_sbpi_model(pools)
        ),
        asyncio.create_task(
            get_sbpb_model(pools)
        ),
        asyncio.create_task(
            get_smp_roll5_model(pools)
        ),
        asyncio.create_task(
            get_smp_roll17_model(pools)
        ),
        asyncio.create_task(
            get_smp_model(pools)
        )
    ]
    
    models = await asyncio.gather(*model_tasks)
    return dict(zip(model_names, models))


async def train_models(
        logdir: str,
        logprefix: str,
        logdayformat: str,
        tz: str,
        lat: float,
        lon: float
) -> int:

    pools = await get_train_pools(
        logdir, logprefix, logdayformat, tz, lat, lon
    )

    return (await get_models(pools)) if pools is not None else None
