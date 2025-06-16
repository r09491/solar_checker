__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import asyncio

import pandas as pd
import numpy as np

from ..typing import (
    List
)
from ..common import (
    t64_from_iso
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


SUN_WEIGHT = 0.7
CLOUD_WEIGHT = 1 - SUN_WEIGHT


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
    skyindex = pd.to_datetime([t64_from_iso(t[:-6]) for t in sky[0].index])
    for s in sky:
        s.set_index(skyindex, inplace = True)

    todaysun = sky[0].sunshine
    todaycover = sky[0].cloud_cover
    
    fromdayswithsun = pd.concat(sky[1:], axis=1)
    fromdayssun = fromdayswithsun.sunshine
    fromdayscover = fromdayswithsun.cloud_cover
        
    """ Scale for values during sunshine """

    k00 = todaysun
    e00 = k00.max()/5 # Soften factor for division by low values
    logger.info(f'Soften factor sun e00 "{e00}"')
    isdataframe = type(fromdayssun) == pd.core.frame.DataFrame
    k01 = fromdayssun.mean(axis=1) if isdataframe else fromdayssun
    sunshine = (k00+e00)/(k01+e00)

    k10 = 100 - todaycover
    e10 = k10.max()/5 # Soften factor clouddivision by low values
    logger.info(f'Soften factor cloud e10 "{e10}"')
    isdataframe = type(fromdayscover) == pd.core.frame.DataFrame
    k11 = 100 - fromdayscover.mean(axis=1) if isdataframe else fromdayscover
    cloud_free = (k10+e10)/(k11+e10)
    
    return (pd.DataFrame(
        index = k00.index,
        data = {
            "SUNSHINE": sunshine,
            "CLOUD_FREE": cloud_free,
            "ADAPTATION": SUN_WEIGHT*sunshine+CLOUD_WEIGHT*cloud_free,
        }
    )) 


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

    w = watts[phase]

    try:
        smp = w.loc[:,'SMP']
        sbpi = w.loc[:,'SBPI']
        sbpo = w.loc[:,'SBPO']            
        sbpb = w.loc[:,'SBPB']
    except KeyError:
        logger.error(f'Samples for phase "{phase}" are missing.')
        return
    
    # Maximum radiation before scaling. Should not be exceeded after scaling!
    max_sbpi = sbpi.max()

    # Do the scaling
    
    issun = sbpi>0
    sunsbpi = sbpi[issun]
    castrise, castset = sunsbpi.index[0], sunsbpi.index[-1]
    logger.info(f'castrise @ "{castrise}", castset @ "{castset}"')
    sunadapt = adapters.resample('T').ffill().loc[castrise:castset, "ADAPTATION"]
    sunsbpi = sunsbpi*sunadapt
    
    logger.info(f'Adapting watts "{phase}" to limits')

    soc = -watts[
        'tomorrowwatts1' if (phase == 'tomorrowwatts2') else 'findwatts'
    ].loc[:,'SBSB'].iloc[-1]*MAX_SBPB
    logger.info(f'"SOC is "{-soc:.0f}Wh"')

    # Calculate the overall power consumption without a solarbank as
    # imported directly from the grid. For unknown reasons there may
    # be negative values which are skipped.
    smp += sbpo
    smp[smp<=0] = 0 # No export to the grid
    sbpb[sbpb>=0] = 0 # No battery discharge
    
    # The calculated radiation may above the system capabilities and
    # has to meet constraints of the used panel
    sbpi[sbpi>max_sbpi] = max_sbpi

    # Maybe only for solix gen1
    sbpb[(sbpi>0) & (sbpi<35)]=-sbpi
    sbpo[(sbpi>0) & (sbpi<35)]=0
    
    # Maybe only for solix gen1
    sbpb[(sbpi>=35) & (sbpi<100)] = 0
    sbpo[(sbpi>=35) & (sbpi<100)] = sbpi[(sbpi>=35) & (sbpi<100)]

    # Concept is to keep battery charging
    sbpo[sbpi>=100] = sbpi[sbpi>=100] + sbpb[sbpi>=100]

    # Fix underrun
    sbpb[sbpo<0] = sbpi[sbpo<0]
    sbpo[sbpo<0] = 0

    """
    # There cannot be more output power then input power
    sbpo[(sbpi>0) & (sbpo>sbpi)] = sbpi

    # Simulate the charging of the solarbank during radiation
    # Note: Discharging part will be overridden
    sbpb[sbpi>0] = sbpo[sbpi>0] - sbpi[sbpi>0]
    sbpb[(sbpi>0) & (sbpb<-MAX_SBPB_CHARGING)] = -MAX_SBPB_CHARGING
    sbpo[sbpi>0] = sbpi[sbpi>0] + sbpb[sbpi>0]
    """
    
    """
    sbpbover = (soc + (sbpb.cumsum()/60)) < -MAX_SBPB
    if sbpbover.any():
        logger.info(f'OVERCHARGE: "{np.where(sbpbover)[0][0]/60:.01f}h"')
    sbpb[sbpbover] = 0
    sbpo[sbpbover] = sbpi[sbpbover]
    """
    """
    sbpbunder = (soc + (sbpb.cumsum()/60)) > -MIN_SBPB
    if sbpbunder.any():
        logger.info(f'UNDERCHARGE: {np.where(sbpbunder)[0][0]/60:0.1f}h"')
    sbpb[sbpbunder] = 0
    sbpo[sbpbunder] = 0
    """

    # Discharge to be the same solarbank export  
    sbpb[sbpi<=0] = sbpo[sbpi<=0] 
    
    # Reduce the needed grid power by the power from the solarbank
    smp -= sbpo

    watts[phase].loc[:,'SMP'] = smp
    watts[phase].loc[:,'SBPB'] = sbpb           
    watts[phase].loc[:,'SBPO'] = sbpo           
    watts[phase].loc[:,'SBPI'] = sbpi
