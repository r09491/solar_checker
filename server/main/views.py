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

    dt = datetime.strptime(logmonth, logdayformat[:-2])
    first = t64(datetime(year=dt.year, month=dt.month, day=1), 'D')
    last = t64(datetime(year=dt.year+dt.month//12, month=dt.month%12+1, day=1), 'D')                               
    mtime = np.arange(first, last, dtype=t64)

    msme = np.zeros(mtime.size, dtype=f64)
    mive1 = np.zeros(mtime.size, dtype=f64)
    mive2 = np.zeros(mtime.size, dtype=f64)
    mspe  = np.zeros(mtime.size, dtype=f64)

    for i, t in enumerate(mtime):
        mld = t.astype(datetime).strftime(logdayformat)
        m = await get_kwh_sum_from_csv(mld, logprefix, logdir)
        msme[i], mive1[i], mive2[i], mspe[i] = m.values()

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
    mkwh  = await get_kwh_bar(*m.values(), price, 0.5, '%d')
    return {'logmonth': logmonth, 'kwh': mkwh}


async def get_kwh_year(logyear: str,
                       logprefix: str,
                       logdir: str,
                       logdayformat:str) -> list:

    first = t64(datetime(year=2000+int(logyear), month=1, day=1), 'M')
    last = t64(datetime(year=2000+int(logyear)+1, month=1, day=1), 'M')                
    ytime = np.arange(first, last, dtype=t64)

    ysme = np.zeros(ytime.size, dtype=f64)
    yive1 = np.zeros(ytime.size, dtype=f64)
    yive2 = np.zeros(ytime.size, dtype=f64)
    yspe  = np.zeros(ytime.size, dtype=f64)

    for i, t in enumerate(ytime):
        ylm = t.astype(datetime).strftime(logdayformat)[:-2]
        ym = await get_kwh_month(ylm,logprefix,logdir,logdayformat)
        yms = [v.sum() for v in list(ym.values())[1:]]
        ysme[i], yive1[i], yive2[i], yspe[i] = yms

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
    ykwh  = await get_kwh_bar(*y.values(), price, 15, '%m')

    return {'logyear': logyear, 'kwh': ykwh}

