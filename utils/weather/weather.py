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

async def get_sky_adapters(
        doi: list,
        lat: float,
        lon: float,
        tz: str) -> pd.DataFrame:

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
    
    k1 = (
        reduce(lambda x,y: x+y, sky[1:])).sunshine / len(sky[1:]
    ) if len(sky[1:])>0 else None
    sunshine = np.array(
        [(v1/v2) if ((v2>0) and (0.25 < (v1/v2) < 2.5)) else 1.0
         for (v1,v2) in zip(k0,k1)]
    ) if k1 is not None else None

    k2 = (100 - (
        reduce(lambda x,y: x+y, sky[1:])).cloud_cover / len(sky[1:]
        )
    ) if len(sky[1:])>0 else None
    cloud_free = np.array(
        [(v1/v2) if ((v2>0) and (0.25 < (v1/v2) < 2.5)) else 1.0
         for (v1,v2) in zip(k0,k2)]
    )if k2 is not None else None
    
    return (pd.DataFrame(
        index = k0.index,
        data = {"SUNSHINE":sunshine, "CLOUD_FREE": cloud_free}
    )[:-1]) if (
        (sunshine is not None) and (cloud_free is not None)
    ) else None


MAX_SBPI = 880

MIN_SBSB = 0.1
MAX_SBSB = 1.0

MIN_SBPB = 160
MAX_SBPB = 1600
MAX_SBPB_CHARGING = 600

""" Apply the sun adapters to the phase """
def apply_sky_adapters( watts: pd.DataFrame,
                        phase: str,
                        adapters: pd.DataFrame) -> pd.DataFrame:

    if adapters is None or watts[phase].empty:
        logger.warning(f'Watts for phase "{phase}" is not modified')
        return #watts

    logger.info(f'Adapting watts "{phase}" to weather')

    # Note: Undercharge and overcharge are not checked.
    
    w =watts[phase]

    # Determine the start for adaptation
    cast_h_first = t64_h_first(w.index[0])

    # Do the cast
    for t in adapters.loc[cast_h_first:].index:
        logger.info(f'SUNSHINE factor for "{t}" is "{adapters.loc[t, "SUNSHINE"]:0.2f}"')
        logger.info(f'CLOUD_FREE factor for "{t}" is "{adapters.loc[t, "CLOUD_FREE"]:0.2f}"')
        try:
            w.loc[t64_h_first(t):t64_h_last(t), ['SBPI']] *= (
                adapters.loc[t, "SUNSHINE"]*adapters.loc[t, "CLOUD_FREE"]
            )
        except KeyError:
            logger.warning(f'Sky adaptation failed for "{t}"')
            

    logger.info(f'Adapting watts "{phase}" to limits')

    try:
        smp = w.loc[cast_h_first:,'SMP']
        sbpi = w.loc[cast_h_first:,'SBPI']
        sbpo = w.loc[cast_h_first:,'SBPO']            
        sbpb = w.loc[cast_h_first:,'SBPB']
        #sbsb = w.loc[cast_h_first:,'SBSB']
    except KeyError:
        logger.error(f'Samples for phase "{cast_h_first}" are missing.')
        return

    #soc = -sbsb.iloc[0]*MAX_SBPB
    soc = -watts[
        'tomorrowwatts1' if (phase == 'tomorrowwatts2') else 'findwatts'
    ].loc[:,'SBSB'].iloc[-1]*MAX_SBPB
    logger.info(f'"SOC is "{-soc:.0f}Wh"')
    
    # Calculate the overall power consumption without a solarbank as
    # imported directly from the grid. For unknown reasons there may
    # be negative values which are skipped.
    smp += sbpo
    smp[smp<=0] = 0 

    # The calculated radiation has to meet system constraints of the used panel
    sbpi[sbpi>MAX_SBPI] = MAX_SBPI

    # There cannot be more output power then input power
    sbpo[(sbpi>0) & (sbpo>sbpi)] = sbpi

    # Simulate the charging of the solarbank during radiation
    # Note: Discharging part will be overridden
    sbpb[sbpi>0] = sbpo[sbpi>0] - sbpi[sbpi>0]
    sbpb[(sbpi>0) & (sbpb<-MAX_SBPB_CHARGING)] = -MAX_SBPB_CHARGING
    sbpo[sbpi>0] = sbpi[sbpi>0] + sbpb[sbpi>0]

    sbpbover = (soc + (sbpb.cumsum()/60)) < -MAX_SBPB
    if sbpbover.any():
        logger.info(f'OVERCHARGE: "{np.where(sbpbover)[0][0]/60:.01f}h"')
    sbpb[sbpbover] = 0
    sbpo[sbpbover] = sbpi[sbpbover]
    
    sbpbunder = (soc + (sbpb.cumsum()/60)) > -MIN_SBPB
    if sbpbunder.any():
        logger.info(f'UNDERCHARGE: {np.where(sbpbunder)[0][0]/60:0.1f}h"')
    sbpb[sbpbunder] = 0
    sbpo[sbpbunder] = 0
        
    
    # Reduce the needed grid power by the power from the solarbank
    smp -= sbpo
    
    watts[phase].loc[cast_h_first:,'SMP'] = smp
    watts[phase].loc[cast_h_first:,'SBPB'] = sbpb           
    watts[phase].loc[cast_h_first:,'SBPO'] = sbpo           
    watts[phase].loc[cast_h_first:,'SBPI'] = sbpi
