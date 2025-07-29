import asyncio
import numpy as np
import pandas as pd
import joblib


from aicast.model import (
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

    sbpi_model = joblib.load(f'{modeldir}/lightgbm_sbpi_model.pkl')
    sbpo_model = joblib.load(f'{modeldir}/lightgbm_sbpo_model.pkl')
    smp_model = joblib.load(f'{modeldir}/lightgbm_smp_model.pkl')

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
    
    # Predict with models, sequence is mandatory
    pool['SBPI'] = sbpi_model.predict(pool[SBPI_FEATURES]).astype(int) 
    pool['SMP'] = smp_model.predict(pool[SMP_FEATURES]).astype(int)
    pool['SBPO'] = sbpo_model.predict(pool[SBPO_FEATURES]).astype(int)

    # Using system knowlegde
    pool['SBPB'] = pool['SBPO'] - pool['SBPI'].astype(int)

    return pool.loc[:, ['TIME', 'SBPI', 'SBPB', 'SBPO', 'SMP']]
