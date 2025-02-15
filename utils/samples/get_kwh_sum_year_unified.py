__doc__=""" Unifies the Calculated energy in kWH for each month of the
specified year.  """
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

from .get_kwh_sum_month_unified import get_kwh_sum_month_unified

async def get_kwh_sum_year_unified(
        logyear: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> list:

    __me__='get_kwh_sum_year_unified'
    logger.info(f'{__me__}: started "{logyear}"')

    dt = datetime.strptime(logyear, logdayformat[:2])
    first = t64(datetime(year=dt.year, month=1, day=1), 'M')
    last = t64(datetime(year=dt.year+1,month=1, day=1), 'M')
    ytime = np.arange(first, last, dtype=t64)

    async def doer(t: t64) -> dict:
        yd = t.astype(datetime).strftime(logdayformat)[:-2]
        ys = await get_kwh_sum_month_unified(
            yd, logprefix,logdir,logdayformat)
        if ys is None: return None
        yss = [v.sum() for v in list(ys.values())[1:]]
        return yss
    results = await asyncio.gather(*[doer(t) for t in ytime])

    ysmeon = np.zeros(ytime.size, dtype=f64)
    ysmeoff = np.zeros(ytime.size, dtype=f64)
    ypanel = np.zeros(ytime.size, dtype=f64)

    for i, r in enumerate(results):
        if r is None: continue
        ysmeon[i], ysmeoff[i], ypanel[i] = r

    logger.info(f'{__me__}: done')        
    return {'TIME':ytime, 'SMEON':ysmeon, 'SMEOFF':ysmeoff,'PANEL':ypanel}        

