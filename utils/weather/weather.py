__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import asyncio

import pandas as pd
import numpy as np

from functools import reduce

from ..typing import (
    List
)
from ..common import (
    t64_first,
    t64_last,
    t64_to_hm,
    t64_from_iso,
    t64_h_next,
    t64_h_first,
    t64_h_last,
    ymd_tomorrow,
    ymd_yesterday,
    ymd_over_t64
    )
from ..common import (
    FORECAST_NAMES
)

from brightsky import(
    Sky
)

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)


""" Get the factors to adapt the average of the closest days to the
current sun situation """

async def get_sun_adapters(
        doi: list,
        lat: float,
        lon: float,
        tz: str) -> pd.Series:

    """ Time is in UTC """
    skytasks = [asyncio.create_task(
        Sky(lat, lon, ld, tz).get_sky_info()
    ) for ld in doi]
    
    """ Get the list of associated columns """
    sky = await asyncio.gather(*skytasks)
    for s in sky:
        if s is None: return None

    """ Unify the indices. Takes care of summertime and wintertime """
    skyindex = np.array([t64_from_iso(t[:-6]) for t in sky[0].index])
    for s in sky:
        s.set_index(skyindex, inplace = True)

    k0 = sky[0].sunshine
    k1 = (reduce(lambda x,y: x+y, sky[1:])).sunshine / len(sky[1:])

    return pd.Series(
        index = k0.index,
        data = [v1/v2 if v2>0 else 1.0 for (v1,v2) in zip(k0,k1)]
    )[:-1]


""" Apply the sun adapters to the phase """
def apply_sun_adapters( slicewatts: pd.DataFrame,
                        adapter: pd.DataFrame) -> pd.DataFrame:

    if adapter is None or slicewatts.empty:
        logger.warning(f'Watts for phase is not modified')
        return slicewatts
    
    t = slicewatts.index[0]
    tt = slicewatts.index[-1]
    while t<tt:
        slicewatts.loc[t64_h_first(t):t64_h_last(t),
                       FORECAST_NAMES] *= adapter[t64_h_first(t)]
        t = t64_h_next(t)
    return slicewatts
