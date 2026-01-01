__doc__=""" Unifies the calculated energy results for each day of the
specified month. One device column is selected best representing the
energy production at that day. If connected the smartplug has priority
1 if it directly connects an inverter to the house.  Priority 2 has
the inverter if data are available. Priority 3 has the solarbank.  """
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

from .get_kwh_sum_month import get_kwh_sum_month

async def get_kwh_sum_month_unified(
        logmonth: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> dict:

    __me__='get_kwh_sum_month_unified'
    logger.info(f'{__me__}: started "{logmonth}"')

    mkwhs = await get_kwh_sum_month(
        logmonth,
        logprefix,
        logdir,
        logdayformat)
    if mkwhs is None:
        logger.info(f'{__me__}: aborted')
        return None

    mtime, msmeon, msmeoff, mive1, mive2, mspeh, msbeo = mkwhs.values()

    # 1.Prio
    umkwhs = mspeh.copy()
    isumkwhs = umkwhs > 0

    # 2.Prio 
    mive = mive1 + mive2
    umkwhs[~isumkwhs] = mive[~isumkwhs]
    isumkwhs = umkwhs > 0

    # 3.Prio
    umkwhs[~isumkwhs] = msbeo[~isumkwhs]

    logger.info(f'{__me__}: started')
    return {'TIME':mtime, 'SMEON':msmeon, 'SMEOFF':msmeoff,'PANEL':umkwhs}
