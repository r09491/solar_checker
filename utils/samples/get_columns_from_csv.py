__doc__="""
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
import asyncio

import numpy as np

from ..typing import(
    f64, f64s, t64, t64s, strings
)

from ..csvlog import(
    get_power_log
)

async def get_columns_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
        
    df = await get_power_log(
        logday=logday,
        logprefix=logprefix,
        logdir=logdir
    )
    
    if df is None:
        logger.error(f'Undefined or erroneous LOG file for "{logday}"')
        return None
    
    return {
        "TIME": df["TIME"].to_numpy() if "TIME" in df else None,
        "SMP" : df["SMP"].to_numpy() if "SMP" in df else np.zeros(df.shape[0]),
        "IVP1": df["IVP1"].to_numpy() if "IVP1" in df else np.zeros(df.shape[0]),
        "IVP2": df["IVP2"].to_numpy() if "IVP2" in df else np.zeros(df.shape[0]),
        "SPPH": df["SPPH"].to_numpy() if "SPPH" in df else np.zeros(df.shape[0]),
        "SBPI": df["SBPI"].to_numpy() if "SBPI" in df else np.zeros(df.shape[0]),
        "SBPO": df["SBPO"].to_numpy() if "SBPO" in df else np.zeros(df.shape[0]),
        "SBPB": df["SBPB"].to_numpy() if "SBPB" in df else np.zeros(df.shape[0]),
        "SBSB" :df["SBSB"].to_numpy() if "SBSB" in df else np.zeros(df.shape[0]),
        "SPP1" :df["SPP1"].to_numpy() if "SPP1" in df else np.zeros(df.shape[0]),
        "SPP2" :df["SPP2"].to_numpy() if "SPP2" in df else np.zeros(df.shape[0]),
        "SPP3" :df["SPP3"].to_numpy() if "SPP3" in df else np.zeros(df.shape[0]),
        "SPP4" :df["SPP4"].to_numpy() if "SPP4" in df else np.zeros(df.shape[0])
    }
