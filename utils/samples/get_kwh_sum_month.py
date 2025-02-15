__doc__=""" Calculates the energy in kWH for each day of the specified
month. Each day has a list of energies. Dependent on the configuration
not all items may have recorded data for each day. Data may be
recorded on different devices."""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import asyncio

from datetime import datetime

import numpy as np

from ..typing import(
    f64, t64
)

from .get_kwh_sum_from_csv import get_kwh_sum_from_csv

async def get_kwh_sum_month(logmonth: str,
                            logprefix: str,
                            logdir: str,
                            logdayformat:str) -> dict:

    __me__='get_kwh_sum_month'
    logger.info(f'{__me__}: started "{logmonth}"')

    dt = datetime.strptime(logmonth, logdayformat[:-2])
    first = t64(datetime(year=dt.year,
                         month=dt.month, day=1), 'D')
    last = t64(datetime(year=dt.year+dt.month//12,
                        month=dt.month%12+1, day=1), 'D')                               
    mtime = np.arange(first, last, dtype=t64)

    async def doer(t: t64) -> dict:
        md = t.astype(datetime).strftime(logdayformat)
        ms = await get_kwh_sum_from_csv(md, logprefix, logdir)
        if ms is None: return None
        return ms.values()
    doertasks = [asyncio.create_task(doer(t)) for t in mtime]
    results = await asyncio.gather(*doertasks)

    """ Initialise the samples for the month """
    
    msmeon = np.zeros(mtime.size, dtype=f64)
    msmeoff = np.zeros(mtime.size, dtype=f64)
    mive1 = np.zeros(mtime.size, dtype=f64)
    mive2 = np.zeros(mtime.size, dtype=f64)
    mspeh  = np.zeros(mtime.size, dtype=f64)
    msbeo  = np.zeros(mtime.size, dtype=f64)

    """ Overwrite the presets with existing sample data """

    have_result = False
    for i, r in enumerate(results):
        if r is None: continue
        have_result = True
        msmeon[i], msmeoff[i], mive1[i], mive2[i], mspeh[i], msbeo[i] = r

    if not have_result:
        logger.info(f'{__me__}: aborted')       
        return None

    logger.info(f'{__me__}: done')       
    return {'TIME':mtime, 'SMEON':msmeon, 'SMEOFF':msmeoff,
            'IVE1':mive1, 'IVE2':mive2, 'SPEH':mspeh, 'SBEO':msbeo}

