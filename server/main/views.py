import asyncio
from aiohttp import web
import aiohttp_jinja2

from datetime import datetime

from typing import Any
from utils.types import f64, timeslots
from utils.samples import get_columns_from_csv
from utils.plots import get_w_image, get_wh_image


@aiohttp_jinja2.template('plot_power.html')
async def plot_power(request: web.Request) -> dict:

    conf = request.app['conf']
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']
    price = conf['energy_price']
    slots = conf['power_slots']
    
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
    w, wh = await asyncio.gather(
        get_w_image(time, smp, ivp1, ivp2, spp, slots),
        get_wh_image(time, sme, ive1, ive2, spp, price),
    )

    return {'logday': logday, 'w': w, 'wh': wh}

