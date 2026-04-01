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
)
from utils.common import (
    ymd_tomorrow,
    ymd_yesterday
)
from utils.plots import (
    get_w_line,
    get_kwh_line,
)
from utils.predicts import (
    predict_naive_today,
    predict_naive_custom,
    get_predict_tables
)


@aiohttp_jinja2.template('plot_predict_naive.html')
async def plot_predict_naive(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    full_wh = conf['battery_full_wh']
    full_kwh = full_wh / 1000
    empty_kwh = conf['battery_min_percent'] /100 * full_kwh
    
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']

    lat, lon, tz = conf['lat'], conf['lon'], conf['tz']

    today = datetime.strftime(datetime.now(), logdayformat)

    try:
        castday = request.match_info['castday']
    except KeyError:
        castday = None

    try:
        cover = request.match_info['cover']
    except KeyError:
        cover = None

    cover_24 = (np.array(24*[0]) if cover == 'blue' else \
                np.array(24*[60]) if cover == 'white' else
                np.array(24*[100]) if cover == 'grey' else None)
    
    if castday is None:
        cast = await predict_naive_today(
            lat = lat,
            lon = lon,
            logprefix = logprefix,
            logdir = logdir
        )
    else:
        cast = await predict_naive_custom(
            castday = castday,
            cover = cover_24,
            lat = lat,
            lon = lon,
            logprefix = logprefix,
            logdir = logdir
        )

    _, casthours, realstop, caststart = cast if cast  is not None else 4*(None)        
    if (casthours is None) or (caststart is None):
        return aiohttp_jinja2.render_template(
            "plot_predict_naive_error.html", request,
            {'today': today,
             'castday': castday,
             'casttomorrow': ymd_tomorrow(castday if castday is not None else today),
             'castyesterday': ymd_yesterday(castday if castday is not None else today),
             "error" : f'No log files found or no irridiance'}
        )

    time = np.array(casthours.index)
    sbpi = np.array(casthours['SBPI']) if 'SBPI' in casthours else None
    sbpo = np.array(casthours['SBPO']) if 'SBPO' in casthours else None
    sbpb = np.array(casthours['SBPB']) if 'SBPB' in casthours else None
    sbsb = np.array(casthours['SBSB']) if 'SBSB' in casthours else None
    ivp1 = np.array(casthours['IVP1']) if 'IVP1' in casthours else None
    ivp2 = np.array(casthours['IVP2']) if 'IVP2' in casthours else None
    spph = np.array(casthours['SPPH']) if 'SPPH' in casthours else None
    smp = np.array(casthours['SMP']) if 'SMP' in casthours else None

    smpon = smp.copy() if smp is not None else None
    if smpon is not None:
        smpon[smpon<0] = 0
    smpoff = -smp.copy() if smp is not None else None
    if smpoff is not None:
        smpoff[smpoff<0] =0

    sbpbcharge = -sbpb.copy() if sbpb is not None else None
    if sbpbcharge is not None:
        sbpbcharge[sbpbcharge<0] =0
    sbpbdischarge = sbpb.copy() if sbpb is not None else None
    if sbpbdischarge is not None:
        sbpbdischarge[sbpbdischarge<0] =0

    tphases = [realstop, caststart, caststart, time[-1]]

    w, kwh = await asyncio.gather(
        get_w_line(
            time,
            smp,
            ivp1,
            ivp2,
            spph,
            sbpi,
            sbpo,
            sbpb,
            tphases = tphases
        ),
        get_kwh_line(
            time,
            smpon.cumsum()/1000 if smpon is not None else None,
            smpoff.cumsum()/1000 if smpoff is not None else None,
            ivp1.cumsum()/1000 if ivp1 is not None else None,
            ivp2.cumsum()/1000 if ivp2 is not None else None,
            spph.cumsum()/1000 if spph is not None else None,
            sbpi.cumsum()/1000 if sbpi is not None else None,
            sbpo.cumsum()/1000 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000 if sbpbcharge is not None else None,
            sbpbdischarge.cumsum()/1000 if sbpbdischarge is not None else None,
            sbsb*full_kwh if sbsb is not None else None,
            empty_kwh,
            full_kwh,
            price[castday[:2] if castday is not None else today[:2]],
            tphases = tphases
        )
    )

    predicttables = await get_predict_tables(casthours)
    if predicttables is None:
        return aiohttp_jinja2.render_template(
            "plot_predict_naive_error.html", request,
            {'today': today,
             'castday': castday,
             'casttomorrow': ymd_tomorrow(castday if castday is not None else today),
             'castyesterday': ymd_yesterday(castday if castday is not None else today),
             "error" : f'Cannot output predict tables for "{castday}"'}
        )

    return {'today': today,
            'cover': cover,
            'castday': castday,
            'casttomorrow': ymd_tomorrow(castday if castday is not None else today),
            'castyesterday': ymd_yesterday(castday if castday is not None else today),
            'w': w,
            'kwh': kwh,
            'predicttables': predicttables}
