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

from datetime import(
    datetime,
    timedelta
)

from utils.typing import (
    f64, f64s, t64, t64s, timeslots
)
from utils.common import (
    ymd_yesterday,
    ymd_tomorrow,
)
from utils.plots import (
    get_w_line,
    get_kwh_line,
)
from aicast.predict_models import (
    predict_models
)
from aicast.result_tables import (
    get_predict_tables
)

@aiohttp_jinja2.template('plot_ai_cast.html')
async def plot_ai_cast(request: web.Request) -> dict:

    if sys.version_info < (3, 11):
        return aiohttp_jinja2.render_template(
            'error.html', request,
            {'error' : f'AI cast cannot run on this system.Upgrade!'}
    )

    conf = request.app['conf']

    price = conf['energy_price']
    full_wh = conf['battery_full_wh']
    full_kwh = full_wh / 1000
    empty_kwh = conf['battery_min_percent'] /100 * full_kwh
    
    modeldir = conf['modeldir']
    
    tz = conf['tz']
    lat = conf['lat']
    lon = conf['lon']

    logdayformat = conf['logdayformat']
    
    today = datetime.strftime(datetime.now(), logdayformat)
    
    try:
        castday = request.match_info['castday']
    except KeyError:
        castday = today

    castday = today if castday < today else castday
    
    pool = await predict_models(
        castday, tz, lat, lon, modeldir
    )
    if pool is None:
        return aiohttp_jinja2.render_template(
            "error.html", request,
            {"error" : f'Model files for  "{castday}" not found or not valid'}
        )
    
    time = np.array(pool['TIME'])
    sbpi = np.array(pool['SBPI'])
    sbpo = np.array(pool['SBPO'])
    sbpb = np.array(pool['SBPB'])
    smp = np.array(pool['SMP'])

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<=0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
    sbpbdischarge[sbpb>0] = sbpb[sbpb>0]

    
    sbeb = sbpb.cumsum()/1000/60 if sbpb is not None else None
    sbeb = (empty_kwh + sbeb.max() - sbeb) if sbeb is not None else None
    pool['SBSB'] = 100*sbeb/full_kwh if sbeb is not None else None
    
    w, kwh = await asyncio.gather(
        get_w_line(
            time,
            smp,
            None,
            None,
            None,
            sbpi,
            sbpo,
            sbpb,
            tz=tz
        ),
        get_kwh_line(
            time,
            smpon.cumsum()/1000/60 if smpon is not None else None,
            smpoff.cumsum()/1000/60 if smpoff is not None else None,
            None,
            None,
            None,
            sbpi.cumsum()/1000/60 if sbpi is not None else None,
            sbpo.cumsum()/1000/60 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000/60 if sbpbcharge is not None else None,
            sbpbdischarge.cumsum()/1000/60 if sbpbdischarge is not None else None,
            sbeb if sbeb is not None else None,
            empty_kwh,
            full_kwh,
            price[castday[:2]],
            tz=tz
        )
    )

    predicttables = await get_predict_tables(pool)
    if predicttables is None:
        return aiohttp_jinja2.render_template(
            "error.html", request,
            {"error" : f'Cannot output predict tables for "{castday}"'}
        )

    return {'castday': castday,
            'castyesterday': ymd_yesterday(castday),
            'casttomorrow': ymd_tomorrow(castday),
            'w': w,
            'kwh': kwh,
            'predicttables': predicttables}
