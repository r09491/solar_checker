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
        "TIME": df["TIME"].to_numpy(),
        "SMP" : df["SMP"].to_numpy(),
        "IVP1": df["IVP1"].to_numpy(),
        "IVP2": df["IVP2"].to_numpy(),
        "SPPH": df["SPPH"].to_numpy(),
        "SBPI": df["SBPI"].to_numpy(),
        "SBPO": df["SBPO"].to_numpy(),
        "SBPB": df["SBPB"].to_numpy(),
        "SBSB" :df["SBSB"].to_numpy(),
        "SPP1" :df["SPP1"].to_numpy(),
        "SPP2" :df["SPP2"].to_numpy(),
        "SPP3" :df["SPP3"].to_numpy(),
        "SPP4" :df["SPP4"].to_numpy()
    }
