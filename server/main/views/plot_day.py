import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import sys

import asyncio
from aiohttp import web
import aiohttp_jinja2

import numpy as np
import pandas as pd

from datetime import(
    datetime,
    timedelta
)
from utils.common import (
    ymd_yesterday,
    ymd_tomorrow,
    ymd_365_days_ago,
    ymd_365_days_ahead,
)
from utils.samples import (
    get_columns_from_csv, 
)
from utils.plots import (
    get_blocks,
    get_w_line,
    get_kwh_line,
)

@aiohttp_jinja2.template('plot_day.html')
async def plot_day(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    full_wh = conf['battery_full_wh']
    full_kwh = full_wh / 1000
    empty_kwh = conf['battery_min_percent'] /100 * full_kwh
    
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']

    today = datetime.strftime(datetime.now(), logdayformat)
    
    try:
        logday = request.match_info['logday']
    except KeyError:
        logday = today 

    c = await get_columns_from_csv(logday, logprefix, logdir)
    if c is None:
        return aiohttp_jinja2.render_template('error.html', request,
            {'error' : f"Samples logfile '{logday}' not found or not valid"})

    time, spph = c['TIME'], c['SPPH']
    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB'] 
    spp1, spp2, spp3, spp4 = c['SPP1'], c['SPP2'], c['SPP3'], c['SPP4']

    # Override sbpi  with inverter if solix is out, eg low protection
    ivp = ivp1 + ivp2
    isivpoversbpi = (ivp > sbpi) & ~(sbpb>0)
    sbpo[isivpoversbpi] = 0
    sbpb[isivpoversbpi] = 0
    sbpi[isivpoversbpi] = ivp[isivpoversbpi]

    if smp is not None:    
        smpon = np.zeros_like(smp)
        smpoff = np.zeros_like(smp)
        smpon[smp>0] = smp[smp>0]
        smpoff[smp<=0] = -smp[smp<=0]

    if sbpb is not None:        
        sbpbcharge = np.zeros_like(sbpb)
        sbpbdischarge = np.zeros_like(sbpb)
        sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
        sbpbdischarge[sbpb>0] = sbpb[sbpb>0]

    blocks, w, kwh = await asyncio.gather(
        get_blocks(time[-1], smp[-1], ivp1[-1], ivp2[-1],
                   spph[-1] if spph is not None else 0,
                   sbpi[-1] if sbpi is not None else 0,
                   sbpo[-1] if sbpo is not None else 0,
                   sbpb[-1] if sbpb is not None else 0,
                   spp1[-1] if spp1 is not None else 0,
                   spp2[-1] if spp2 is not None else 0,
                   spp3[-1] if spp3 is not None else 0,
                   spp4[-1] if spp4 is not None else 0),
        get_w_line(time, smp, ivp1, ivp2,
                   spph, sbpi, sbpo, sbpb),
        get_kwh_line(time,
            smpon.cumsum()/1000/60 if smpon is not None else None,
            smpoff.cumsum()/1000/60 if smpoff is not None else None,
            ivp1.cumsum()/1000/60 if ivp1 is not None else None,
            ivp2.cumsum()/1000/60 if ivp2 is not None else None,
            spph.cumsum()/1000/60 if spph is not None else None,
            sbpi.cumsum()/1000/60 if sbpi is not None else None,
            sbpo.cumsum()/1000/60 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000/60 if sbpb is not None else None,
            sbpbdischarge.cumsum()/1000/60 if sbpb is not None else None,
            sbsb*full_kwh if sbsb is not None else None,
            empty_kwh, full_kwh, price[logday[:2]]))

    return {'logday': logday,
            'logyesterday': ymd_yesterday(logday),
            'logtomorrow': ymd_tomorrow(logday),
            'log365daysago': ymd_365_days_ago(logday),
            'log365daysahead': ymd_365_days_ahead(logday),
            'blocks': blocks if logday == today else None,
            'w': w, 'kwh': kwh}
