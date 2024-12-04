import asyncio
from aiohttp import web
import aiohttp_jinja2

from datetime import datetime

import numpy as np
import pandas as pd

from typing import Any, Optional
from utils.types import (
    f64, f64s, t64, t64s, timeslots
)
from utils.common import (
    PREDICT_NAMES,
    POWER_NAMES,
    PARTITION_2_VIEW
)
from utils.samples import (
    get_columns_from_csv, 
    get_kwh_sum_month_unified,
    get_kwh_sum_year_unified
)
from utils.predicts import (
    get_logs_as_dataframe,
    find_closest,
    partition_closest_watts,
    get_sun_adaptors,
    apply_sun_adapters,
    fix_prediction_watts,
    concat_today,
    concat_tomorrow,
    concat_total,
    get_predict_table
)
from utils.plots import (
    get_blocks,
    get_w_line,
    get_kwh_line,
    get_kwh_bar_unified
)


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)


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
    sme, ive1, ive2 = c['SME'], c['IVE1'], c['IVE2']
    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB'] 
    spp1, spp2, spp3, spp4 = c['SPP1'], c['SPP2'], c['SPP3'], c['SPP4']

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<=0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
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
    return {'logday': logday, 'blocks': blocks if logday == today else None, 'w': w, 'kwh': kwh}


@aiohttp_jinja2.template('plot_month.html')
async def plot_month(request: web.Request) -> dict:

    __me__='plot_month'

    conf = request.app['conf']
    price = conf['energy_price']
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']

    try:
        logmonth = request.match_info['logmonth']
    except KeyError:
        logmonth = datetime.strftime(datetime.now(), logdayformat[:-2])

    logger.info(f'{__me__}: started "{logmonth}"')

    umkwh = await get_kwh_sum_month_unified(
        logmonth, logprefix, logdir, logdayformat)
    
    umplot  = await get_kwh_bar_unified(
        *umkwh.values(), price[logmonth[:2]], 0.7, '%d%n%a')

    logger.info(f'{__me__}: done')
    return {'logmonth': logmonth, 'kwh': umplot}


@aiohttp_jinja2.template('plot_year.html')
async def plot_year(request: web.Request) -> dict:
    __me__='plot_year'

    conf = request.app['conf']
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logdayformat = conf['logdayformat']
    price = conf['energy_price']
    
    try:
        logyear = request.match_info['logyear']
    except KeyError:
        logyear = datetime.strftime(datetime.now(), logdayformat[:2])

    logger.info(f'{__me__}: started "{logyear}"')
    
    uykwh = await get_kwh_sum_year_unified(
        logyear, logprefix, logdir, logdayformat)        
    uyplot  = await get_kwh_bar_unified(
        *uykwh.values(), price[logyear], 14.0, '%b')

    logger.info(f'{__me__}: done')
    return {'logyear': logyear, 'kwh': uyplot}


@aiohttp_jinja2.template('plot_predict.html')
async def plot_predict(request: web.Request) -> dict:

    conf = request.app['conf']

    price = conf['energy_price']
    full_wh = conf['battery_full_wh'] 
    full_kwh = full_wh / 1000
    empty_wh = conf['battery_min_percent'] / 100 * full_wh
    empty_kwh = conf['battery_min_percent'] / 100 * full_kwh
    
    logdir = conf['logdir']
    logprefix = conf['logprefix']
    logpredictformat = conf['logpredictformat']
    logpredictmaxdays = conf['logpredictmaxdays']
    logpredictdays = conf['logpredictdays']
    logpredictcolumns = conf['logpredictcolumns']

    lat, lon, tz = conf['lat'], conf['lon'], conf['tz']
    
    try:
        logday = request.match_info['logday']
    except KeyError:
        logday = datetime.strftime(datetime.now(), logdayformat)

    try:
        what = request.match_info['what'].capitalize()
    except KeyError:
        what = 'Today'
        
        
    """ Get the dictionary with all the power recordings for logdays """
    logsdf = await get_logs_as_dataframe(
        POWER_NAMES,
        logpredictmaxdays,
        logpredictformat,
        logprefix,
        logdir
    )


    """ Get the start and stop time for the reference slot """
    starttime, stoptime = None, None
    starttime, stoptime, closestdays = await find_closest(
        logsdf, logday, starttime, stoptime, logpredictcolumns
    )
    if (starttime is None or stoptime is None or closestdays is None):
        return aiohttp_jinja2.render_template('error.html', request,
            {'error' : f'No radiation detected for the log day  "{logday}"'}
        )

    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")
    
    predictdays = closestdays.index.values[1:logpredictdays]

    """ Get the prediction slots """
    
    todaydoi, tomorrowdoi, soc, partitions = await partition_closest_watts(
        logsdf,
        starttime,
        stoptime,
        closestdays.head(n=logpredictdays)
    )

    """ Get the sun adapters for today and tomorrow """
    todayadapters, tomorrowadapters = await asyncio.gather(
        get_sun_adaptors(todaydoi, lat, lon, tz),
        get_sun_adaptors(tomorrowdoi, lat, lon, tz)
    )


    """ Apply adapters to all phases with radiation """


    partitions['postwatts'] = apply_sun_adapters(
        partitions['postwatts'], todayadapters)    
    partitions['todaywatts'] = apply_sun_adapters(
        partitions['todaywatts'], todayadapters)

    partitions['tomorrowwatts1'] = apply_sun_adapters(
        partitions['tomorrowwatts1'], tomorrowadapters)
    partitions['tomorrowwatts2'] = apply_sun_adapters(
        partitions['tomorrowwatts2'], tomorrowadapters)


    """ Fix some watts after plausibility check """

    partitions['todaywatts'], _ = fix_prediction_watts(
        partitions['todaywatts'], -soc*full_wh)
    partitions['tomorrowwatts1'], _ = fix_prediction_watts(
        partitions['tomorrowwatts1'])
    partitions['tomorrowwatts2'], _ = fix_prediction_watts(
        partitions['tomorrowwatts2'])
    
    
    # Adapt the relative predict table

    ptable, bat_start_soc = get_predict_table(partitions)
    ptable.rename(columns= PARTITION_2_VIEW, inplace=True)
    ptable.fillna(0, inplace=True)

    """ Assemble the prediction elements """
    if what == 'Today':
        c = concat_today(partitions)
        rtable = ptable[:-2]
        tphase = [starttime, stoptime]
    elif what == 'Tomorrow':
        c = concat_tomorrow(partitions)
        rtable = ptable[-2:]
        tphase = None
    elif what == 'Total':
        c = concat_total(partitions)
        rtable = ptable
        tphase = [starttime, stoptime]

    time = np.array(list(c.index.values))
    spph, smp, ivp1, ivp2 = c['SPPH'], c['SMP'], c['IVP1'], c['IVP2']
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB']
    spp1, spp2, spp3, spp4 = c['SPP1'], c['SPP2'], c['SPP3'], c['SPP4']

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<=0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
    sbpbdischarge[sbpb>0] = sbpb[sbpb>0]

        
    w, kwh = await asyncio.gather(
        get_w_line(time, smp, ivp1, ivp2,
                   spph, sbpi, sbpo, sbpb, tphase),
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
            sbsb[0]*full_kwh+sbpbcharge.cumsum()/1000/60-sbpbdischarge.cumsum()/1000/60,
                     empty_kwh, full_kwh, price[logday[:2]], tphase))

    atable = pd.concat([rtable.iloc[:,:2],
                        rtable.iloc[:,2:].cumsum()], axis = 1)
    #atable['BAT>'] =  ptable['BAT>'].cumsum() - full_wh*bat_start_soc 
    atable['START'] = "00:00"
    
    return {'what': what,
            'logday': logday,
            'w': w, 'kwh': kwh,
            'start': start, 'stop': stop,
            'predictdays': predictdays,
            'predicttables': [rtable, atable]}
