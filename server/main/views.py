import asyncio
from aiohttp import web
import aiohttp_jinja2

from datetime import datetime

import numpy as np

from typing import Any, Optional
from utils.types import f64, f64s, t64, t64s, timeslots
from utils.samples import get_columns_from_csv, get_kwh_sum_month, get_kwh_sum_year
from utils.plots import get_w_line, get_kwh_line, get_kwh_bar


@aiohttp_jinja2.template('plot_day.html')
async def plot_day(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    slots = conf['power_slots']
    full_kwh = conf['battery_full_wh'] / 1000
    empty_kwh = conf['battery_min_percent'] /100 * full_kwh
    
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
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB']
    w, kwh = await asyncio.gather(
        get_w_line(time, smp, ivp1, ivp2, spp, sbpi, sbpo, sbpb, slots),
        get_kwh_line(time, sme, ive1, ive2,
            spp.cumsum()/1000/60 if spp is not None else None,
            sbpi.cumsum()/1000/60 if sbpi is not None else None,
            sbpo.cumsum()/1000/60 if sbpo is not None else None,
            sbpb.cumsum()/1000/60 if sbpb is not None else None,
            sbsb*full_kwh if sbsb is not None else None,
            empty_kwh, full_kwh, price))
    return {'logday': logday, 'w': w, 'kwh': kwh}


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

    m = await get_kwh_sum_month(logmonth, logprefix, logdir, logdayformat)        
    mkwh  = await get_kwh_bar(*m.values(), price, 0.7, '%d%n%a')
    return {'logmonth': logmonth, 'kwh': mkwh}

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

    y = await get_kwh_sum_year(logyear, logprefix, logdir, logdayformat)        
    ykwh  = await get_kwh_bar(*y.values(), price, 14.0, '%b')

    return {'logyear': logyear, 'kwh': ykwh}
