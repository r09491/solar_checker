__doc__=""" Calculates the energy in kWH for each column in the record
file """
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import asyncio

import numpy as np

from .get_columns_from_csv import get_columns_from_csv

async def get_kwh_sum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:

    __me__='get_kwh_sum_month'
    logger.info(f'{__me__}: started "{logday}"')
    c = await get_columns_from_csv(logday,logprefix, logdir)
    if c is None:
        logger.info(f'{__me__}: aborted')
        return None
    logger.info(f'{__me__}: done')
    
    smp = c['SMP'] if c and 'SMP' in c else None

    smpon = np.zeros_like(smp) if smp is not None else None
    if smpon is not None:
        issmpon = smp>0
        smpon[issmpon] = smp[issmpon]
        
    smpoff = np.zeros_like(smp) if smp is not None else None
    if smpoff is not None:
        issmpoff = smp<=0
        smpoff[issmpoff] = smp[issmpoff]

    return {'SMEON'  : smpon.sum()/60.0/1000.0 if smpon is not None else 0.0,
            'SMEOFF' : smpoff.sum()/60.0/1000.0 if smpoff is not None else 0.0,
            'IVE1'   : c['IVP1'].sum()/60.0/1000.0 if c and 'IVP1' in c else 0.0,
            'IVE2'   : c['IVP2'].sum()/60.0/1000.0 if c and 'IVP2' in c else 0.0,
            'SPEH'   : c['SPPH'].sum()/60.0/1000.0 if c and 'SPPH' in c else 0.0,
            'SBEO'   : c['SBPO'].sum()/60.0/1000.0 if c and 'SBPO' in c else 0.0}

