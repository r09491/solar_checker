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
current sky situation """

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
        
    todaysun = sky[0].sunshine 
    istodaysun = todaysun>0

    """ Scale for values during sunshine """
    
    k00 = todaysun[istodaysun]
    e00 = k00.max()/5 # Soften factor for division by low values
    logger.info(f'Soften factor e00 "{e00}"')

    k01 = (
        reduce(lambda x,y: x+y, sky[1:])).sunshine[istodaysun] / len(sky[1:]
    ) if len(sky[1:])>0 else None

    sunshine = (np.array(k00)+e00)/(np.array(k01)+e00) if k01 is not None else None

    
    todaycover = sky[0].cloud_cover 
    k10 = 100 - todaycover[istodaysun]
    e10 = k10.max()/5 # Soften factor division by low values
    logger.info(f'Soften factor e10 "{e10}"')
    
    k11 = (100 - (
        reduce(lambda x,y: x+y, sky[1:])).cloud_cover[istodaysun] / len(sky[1:]
        )
    ) if len(sky[1:])>0 else None

    cloud_free = (np.array(k10)+e10)/(np.array(k11)+e10) if k11 is not None else None
    
    return (pd.DataFrame(
        index = k00.index,
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

SUN_WEIGHT = 0.7
CLOUD_WEIGHT = 1 - SUN_WEIGHT

""" Apply the sun adapters to the phase """
def apply_sky_adapters( watts: pd.DataFrame,
                        phase: str,
                        adapters: pd.DataFrame) -> pd.DataFrame:

    if adapters is None or watts[phase].empty:
        logger.warning(f'Watts for phase "{phase}" is not modified')
        return #watts

    logger.info(f'Adapting watts "{phase}" to weather')

    
    # Note: Undercharge and overcharge are not checked.

    w = watts[phase]
    
    # Maximum radiation before scaling. Should not be exceeded after scaling!
    max_sbpi = w.loc[:,"SBPI"].max()

    
    # Determine the start for adaptation
    cast_h_first = t64_h_first(w.index[0])

    # Do the cast
    for t in adapters.loc[cast_h_first:].index:
        logger.info(f'SUNSHINE factor for "{t}" is "{adapters.loc[t, "SUNSHINE"]:0.2f}"')
        logger.info(f'CLOUD_FREE factor for "{t}" is "{adapters.loc[t, "CLOUD_FREE"]:0.2f}"')
        try:
            w.loc[t64_h_first(t):t64_h_last(t), ['SBPI']] *= (
                SUN_WEIGHT*adapters.loc[t, "SUNSHINE"]+CLOUD_WEIGHT*adapters.loc[t, "CLOUD_FREE"]
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
    sbpi[sbpi>max_sbpi] = max_sbpi

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
