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

from utils.plots import (
    get_w_line,
    get_kwh_line,
)
from utils.predicts import (
    Script_Arguments,
    predict_primitive,
    get_predict_tables
)


@aiohttp_jinja2.template('plot_predict_primitive.html')
async def plot_predict_primitive(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    full_wh = conf['battery_full_wh']
    full_kwh = full_wh / 1000
    empty_kwh = conf['battery_min_percent'] /100 * full_kwh

    tz = conf['tz']

    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']
    
    today = datetime.strftime(datetime.now(), logdayformat)
    
    try:
        castday = request.match_info['castday']
    except KeyError:
        castday = ymd_tomorrow(today)

    cast = await predict_primitive(
        Script_Arguments(logprefix, logdir)
    )
    if cast is None:
        return aiohttp_jinja2.render_template(
            "error.html", request,
            {"error" : f'Log files for  "{castday}" not found or not valid'}
        )

    casthours, caststart = cast
    
    time = np.array(casthours.index)
    sbpi = np.array(casthours['SBPI'])
    sbpo = np.array(casthours['SBPO'])
    sbpb = np.array(casthours['SBPB'])
    smp = np.array(casthours['SMP'])

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
    sbpbdischarge[sbpb>0] = sbpb[sbpb>0]

    sbeb = sbpb.cumsum()/1000 if sbpb is not None else None
    sbeb = (empty_kwh + sbeb.max() - sbeb) if sbeb is not None else None
    
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
            smpon.cumsum()/1000 if smpon is not None else None,
            smpoff.cumsum()/1000 if smpoff is not None else None,
            None,
            None,
            None,
            sbpi.cumsum()/1000 if sbpi is not None else None,
            sbpo.cumsum()/1000 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000 if sbpbcharge is not None else None,
            sbpbdischarge.cumsum()/1000 if sbpbdischarge is not None else None,
            sbeb if sbeb is not None else None,
            empty_kwh,
            full_kwh,
            price[castday[:2]],
            tz=tz
        )
    )

    predicttables = await get_predict_tables(casthours)
    if predicttables is None:
        return aiohttp_jinja2.render_template(
            "error.html", request,
            {"error" : f'Cannot output predict tables for "{castday}"'}
        )

    return {'castday': castday,
            'w': w,
            'kwh': kwh,
            'predicttables': predicttables}
