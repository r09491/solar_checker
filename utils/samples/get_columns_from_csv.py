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

from datetime import datetime

from ..typing import(
    f64, f64s, t64, t64s, strings
)
from ..common import(
    SAMPLE_NAMES,
    t64_from_iso
)

from ..csvlog import get_log


def _str2float(value: str) -> f64:
    try:
        return f64(value)
    except:
        return None
    
async def get_columns_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
        
    df = await get_log(
        logcols=SAMPLE_NAMES,
        logday=logday,
        logprefix=logprefix,
        logdir=logdir
    )

    if df is None:
        logger.error(f'Undefined LOG file')
        return None
    
    """ The timestamps """
    time = np.array(df.TIME.apply(t64_from_iso))

    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(_str2float))
    if np.isnan(smp).any():
        logger.error(f'{__me__}:Undefined SMP samples')
        return None
    
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(_str2float))
    if np.isnan(ivp1).any():
        logger.error(f'{__me__}:Undefined IVP1 samples')
        return None

    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(_str2float))
    if np.isnan(ivp2).any():
        logger.error(f'{__me__}:Undefined IVP2 samples')
        return None

    """ The normalised smartmeter energy samples """
    sme = np.array(df.SME.apply(_str2float))
    if np.isnan(sme).any():
        logger.error(f'{__me__}:Undefined SME samples')
        return None
    
    """ The normalised inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(_str2float))
    if np.isnan(ive1).any():
        logger.error(f'{__me__}:Undefined IVE2 samples')
        return None
    
    """ The normalised inverter energy samples channel 2 """
    ive2 = np.array(df.IVE2.apply(_str2float))
    if np.isnan(ive2).any():
        logger.error(f'{__me__}:Undefined IVE2 samples')
        return None

    """ The normalised smartplug power home"""
    spph = np.array(df.SPPH.apply(_str2float))
    if np.isnan(spph).any():
        logger.error(f'{__me__}:Undefined SPPH samples')
        return None

    """ The normalised solarbank power input """
    sbpi = np.array(df.SBPI.apply(_str2float))
    if np.isnan(sbpi).any():
        logger.warn(f'{__me__}:Undefined SBPI samples')
        sbpi = None

    """ The normalised solarbank power output """
    sbpo = np.array(df.SBPO.apply(_str2float))
    if np.isnan(sbpo).any():
        logger.warn(f'{__me__}:Undefined SBPO samples')
        spbo = None

    """ The normalised solarbank power battery """
    sbpb = np.array(df.SBPB.apply(_str2float))
    if np.isnan(sbpb).any():
        logger.warn(f'{__me__}:Undefined SBPB samples')
        sbpb =  None

    """ The normalised solarbank power state of charge """
    sbsb = np.array(df.SBSB.apply(_str2float))
    if np.isnan(sbsb).any():
        logger.warn(f'{__me__}:Undefined SBSB samples')
        sbsb = None

    """ The normalised smartplug power switch 1 """
    spp1 = np.array(df.SPP1.apply(_str2float))
    if np.isnan(spp1).any():
        logger.warn(f'{__me__}:Undefined SPP1 samples')
        #spp1 =  None

    """ The normalised smartplug power switch 2 """
    spp2 = np.array(df.SPP2.apply(_str2float))
    if np.isnan(spp2).any():
        logger.warn(f'{__me__}:Undefined SPP2 samples')
        #spp2 =  None

    """ The normalised smartplug power switch 3 """
    spp3 = np.array(df.SPP3.apply(_str2float))
    if np.isnan(spp3).any():
        logger.warn(f'{__me__}:Undefined SPP3 samples')
        #spp3 =  None

    """ The normalised smartplug power switch 3 """
    spp4 = np.array(df.SPP4.apply(_str2float))
    if np.isnan(spp4).any():
        logger.warn(f'{__me__}:Undefined SPP4 samples')
        #spp4 =  None
        
    # Get rid of offsets and fill tails

    sme -= sme[0]
    sme[sme<0.0] = 0.0
    sme[np.argmax(sme)+1:] = sme[np.argmax(sme)]

    ive1[ive1<0.0] = 0.0
    ive1 -= ive1[0]
    ive1[np.argmax(ive1)+1:] = ive1[np.argmax(ive1)]

    ive2 -= ive2[0]
    ive2[ive2<0.0] = 0.0
    ive2[np.argmax(ive2)+1:] = ive2[np.argmax(ive2)]

    return {'TIME' : time,
            'SMP' : smp, 'IVP1' : ivp1, 'IVP2' : ivp2,
            'SME' : sme, 'IVE1' : ive1, 'IVE2' : ive2, 'SPPH' : spph,
            'SBPI' : sbpi, 'SBPO' : sbpo, 'SBPB' : sbpb, 'SBSB' : sbsb,
            'SPP1' : spp1, 'SPP2' : spp2, 'SPP3' : spp3, 'SPP4' : spp4}
