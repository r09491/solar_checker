__doc__=""" Calculates the energy in kWH for each month of the
specified year. Each month has a list of energies. Dependent on the
configuration not all items may have recorded data for each
month. During a month the energy may be recorded by different
devices. """
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
async def get_kwh_sum_year(
        logyear: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> list:

    __me__='get_kwh_sum_year'
    logger.info(f'{__me__}: started "{logyear}"')

    dt = datetime.strptime(logyear, logdayformat[:2])
    first = t64(datetime(year=dt.year, month=1, day=1), 'M')
    last = t64(datetime(year=dt.year+1,month=1, day=1), 'M')
    ytime = np.arange(first, last, dtype=t64)
    
    async def doer(t: t64) -> dict:
        yd = t.astype(datetime).strftime(logdayformat)[:-2]
        ys = await get_kwh_sum_month(yd,logprefix,logdir,logdayformat)
        if ys is None: return None
        yss = [v.sum() for v in list(ys.values())[1:]]
        return yss
    doertasks = [asyncio.create_task(doer(t)) for t in ytime]
    results = await asyncio.gather(*doertasks)

    ysmeon = np.zeros(ytime.size, dtype=f64)
    ysmeoff = np.zeros(ytime.size, dtype=f64)
    yive1 = np.zeros(ytime.size, dtype=f64)
    yive2 = np.zeros(ytime.size, dtype=f64)
    yspeh  = np.zeros(ytime.size, dtype=f64)
    ysbeo  = np.zeros(ytime.size, dtype=f64)

    for i, r in enumerate(results):
        if r is None: continue
        ysmeon[i], ysmeoff[i], yive1[i], yive2[i], yspeh[i], ysbeo[i] = r

    logger.info(f'{__me__}: done')        
    return {'TIME':ytime, 'SMEON':ysmeon, 'SMEOFF':ysmeoff,
            'IVE1':yive1, 'IVE2':yive2, 'SPEH':yspeh, 'SBEO':ysbeo}        
