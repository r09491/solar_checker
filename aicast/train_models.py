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


from utils.typing import (
    Optional, Any, Dict, List
)

from aicast.model_features import (
    SBPI_FEATURES,
    SBPO_FEATURES,
    SMP_FEATURES
)

from aicast.get_model_pools import (
    get_train_pools
)


async def get_model(
        X: pd.DataFrame,
        y: pd.DataFrame
) -> Any:

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = lgb.LGBMRegressor(
        n_estimators=125,
        learning_rate=0.05
    )
    model.fit(
        X_train, y_train, eval_set=[(X_val, y_val)]
    )

    return model


async def get_sbpi_model(pools: pd.DataFrame) -> Optional[Any]:
    
    model = await get_model(X=pools[SBPI_FEATURES], y=pools['SBPI'])
    return model


async def get_sbpo_model(pools: pd.DataFrame) -> Optional[Any]:

    model = await get_model(X=pools[SBPO_FEATURES], y=pools['SBPO'])
    return model


async def get_smp_model(pools: pd.DataFrame) -> Optional[Any]:

    model = await get_model(X=pools[SMP_FEATURES], y=pools['SMP'])
    return model


async def get_models(pools: pd.DataFrame) -> Optional[Any]:

    model_tasks = [
        asyncio.create_task(
            get_sbpi_model(pools)
        ),
        asyncio.create_task(
            get_sbpo_model(pools)
        ),
        asyncio.create_task(
            get_smp_model(pools)
        )
    ]
    
    models = await asyncio.gather(*model_tasks)
    return models


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
