import asyncio
from aiohttp import web
import aiohttp_jinja2

from datetime import datetime

import numpy as np

from typing import Any, Optional
from utils.types import f64, f64s, t64, t64s, timeslots
from utils.samples import get_logdays, get_columns_from_csv, get_kwh_sum_from_csv
from utils.plots import get_w_line, get_kwh_line, get_kwh_bar


@aiohttp_jinja2.template('plot_day.html')
async def plot_day(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    slots = conf['power_slots']
    
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']

    try:
        logday = request.match_info['logday']
    except KeyError:
        logday = datetime.strftime(datetime.now(), logdayformat)

    c = await get_columns_from_csv(logday, logprefix, logdir)
    if c is None:
        return aiohttp_jinja2.render_template('error.html', request,
            {'error' : f"Samples logfile '{logday}' not found or not valid"})

    time, spp = c['TIME'], c['SPP']
    sme, ive1, ive2 = c['SME'], c['IVE1'], c['IVE2']
    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']
    w, kwh = await asyncio.gather(
        get_w_line(time, smp, ivp1, ivp2, spp, slots),
        get_kwh_line(time, sme, ive1, ive2, spp.cumsum()/1000/60, price),
    )
    return {'logday': logday, 'w': w, 'kwh': kwh}


async def get_kwh_month(logmonth: str,
                        logprefix: str,
                        logdir: str,
                        logdayformat:str) -> Optional[dict]:
    
    lds = await get_logdays(logprefix, logdir)
    mlds = [ld for ld in lds if ld[:-2] == logmonth]
    if len(mlds) == 0:
        return None

    msme = np.arange(len(mlds), dtype=f64)
    mive1 = np.arange(len(mlds), dtype=f64)  
    mive2 = np.arange(len(mlds), dtype=f64)
    mspe  = np.arange(len(mlds), dtype=f64)
    for i, mld in enumerate(mlds):
        kwh_sum = await get_kwh_sum_from_csv(mld, logprefix, logdir)
        msme[i] = kwh_sum['SME']
        mive1[i] = kwh_sum['IVE1']
        mive2[i] = kwh_sum['IVE2']
        mspe[i] = kwh_sum['SPE']

    # Dump nans
    msme[np.isnan(msme)] = 0.0
    mive1[np.isnan(mive1)] = 0.0
    mive2[np.isnan(mive2)] = 0.0
    mspe[np.isnan(mspe)] = 0.0

    def str2date(value: str) -> t64:
        dt = datetime.strptime(value, logdayformat)
        return t64(datetime(year=dt.year, month=dt.month, day=dt.day), 'D')    
    mtime = np.arange(str2date(mlds[0]),
                      str2date(mlds[-1])+1, dtype=t64)
    
    return {'TIME':mtime, 'SME':msme, 'IVE1':mive1, 'IVE2':mive2, 'SPE':mspe}

    
@aiohttp_jinja2.template('plot_month.html')
async def plot_month(request: web.Request) -> dict:

    conf = request.app['conf']
    price = conf['energy_price']
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']

    try:
        logmonth = request.match_info['logmonth']
    except KeyError:
        logmonth = datetime.strftime(datetime.now(), logdayformat[:-2])

    m = await get_kwh_month(logmonth, logprefix, logdir, logdayformat)        
    mkwh  = await get_kwh_bar(*m.values(), price, '%dd')
    return {'logmonth': logmonth, 'kwh': mkwh}


async def get_kwh_year(logyear: str,
                       logprefix: str,
                       logdir: str,
                       logdayformat:str) -> list:

    ysme = np.arange(12, dtype=f64)
    yive1 = np.arange(12, dtype=f64)  
    yive2 = np.arange(12, dtype=f64)
    yspe  = np.arange(12, dtype=f64)
    for i in range(12):
        lm = datetime(year=int(logyear), month=i+1, day=1)
        logmonth = lm.strftime(logdayformat[:-2])
        m = await get_kwh_month(logmonth,logprefix,logdir,logdayformat)
        ysme[i] = 0.0 if m is None else m['SME'].sum()
        yive1[i]= 0.0 if m is None else m['IVE1'].sum()
        yive2[i]= 0.0 if m is None else m['IVE2'].sum()
        yspe[i] = 0.0 if m is None else m['SPE'].sum()

    # Dump nans
    ysme[np.isnan(ysme)] = 0.0
    yive1[np.isnan(yive1)] = 0.0
    yive2[np.isnan(yive2)] = 0.0
    yspe[np.isnan(yspe)] = 0.0
    
    first = t64(datetime(year=2000+int(logyear), month=1, day=1), 'M')
    last = t64(datetime(year=2000+int(logyear)+1, month=1, day=1), 'M')                
    ytime = np.arange(first, last, dtype=t64)

    return {'TIME':ytime, 'SME':ysme, 'IVE1':yive1, 'IVE2':yive2, 'SPE':yspe}        



@aiohttp_jinja2.template('plot_year.html')
async def plot_year(request: web.Request) -> dict:

    conf = request.app['conf']
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']
    price = conf['energy_price']
    slots = conf['power_slots']
    
    try:
        logyear = request.match_info['logyear']
    except KeyError:
        logyear = datetime.strftime(datetime.now(), logdayformat[:2])

    y = await get_kwh_year(logyear, logprefix, logdir, logdayformat)        
    ykwh  = await get_kwh_bar(*y.values(), price, '%mm')

    return {'logyear': logyear, 'kwh': ykwh}

