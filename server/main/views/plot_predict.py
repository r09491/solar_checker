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
    PARTITION_2_VIEW,
)

from utils.csvlog import (
    get_windowed_logs_df,
)
from utils.weather import(
    get_sky_adapters,
    apply_sky_adapters,
)
from utils.predicts.predict_minute import (
    find_closest,
    partition_closest_watts,
    concat_today,
    concat_tomorrow,
    concat_total,
    get_predict_table
)
from utils.plots import (
    get_w_line,
    get_kwh_line,
)

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
    logpredictwindow = conf['logpredictwindow']
    logpredictdays = conf['logpredictdays']
    logpredictcolumns = conf['logpredictcolumns']

    lat, lon, tz = conf['lat'], conf['lon'], conf['tz']

    castfindhours = conf['castfindhours']
    
    try:
        logday = request.match_info['logday']
    except KeyError:
        logday = datetime.strftime(datetime.now(), logdayformat)

    try:
        what = request.match_info['what'].capitalize()
    except KeyError:
        what = 'Today'
        
        
    """ Get the dictionary with all the power recordings for logdays """
    logsdf = await get_windowed_logs_df(
        logpredictwindow,
        logprefix,
        logdir
    )

    """ Preset the start and stop time for the find slot """
    issbpion = logsdf.loc[logday, 'SBPI']>0 # radiation
    timesbpion = logsdf.loc[logday, 'TIME'][issbpion] if (
        issbpion.any()
    ) else None

    stoptime = pd.to_datetime(timesbpion.iloc[-1])  if (
        (timesbpion is not None) and
        (castfindhours is not None)
    ) else None
    starttime = (stoptime - timedelta(hours=castfindhours)) if (
        (stoptime is not None) and
        (castfindhours is not None)
    ) else None
    
    
    """ Get the list of closest days to the logday. The start and stop
    time may be overriden as per real radiation """
    starttime, stoptime, closestdays = await find_closest(
        logsdf, logday, starttime, stoptime, logpredictcolumns
    )        
    if ((starttime is None) and (stoptime is None) and (closestdays is None)):
        return aiohttp_jinja2.render_template(
            'error.html', request,
            {'error' : f'No radiation detected for the log day  "{logday}"'}
        )

    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")

    if ((closestdays is None)):
        return aiohttp_jinja2.render_template(
            'error.html', request,
            {'error' : f'Samples not montonic between "{start}" and "{stop}" for logday "{logday}"'}
        )

    
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
        get_sky_adapters(todaydoi, lat, lon, tz),
        get_sky_adapters(tomorrowdoi, lat, lon, tz)
    )


    """ Apply adapters to all phases with radiation """

    """
    >>> No overcharge/undercharge check
    """
    apply_sky_adapters(
        partitions, 'todaywatts', todayadapters)
    apply_sky_adapters(
        partitions, 'tomorrowwatts1', tomorrowadapters)
    apply_sky_adapters(
        partitions, 'tomorrowwatts2', tomorrowadapters)
    
    # Adapt the relative predict table

    ptable, bat_start_soc = get_predict_table(partitions)
    ptable.rename(columns= PARTITION_2_VIEW, inplace=True)
    ptable.fillna(0, inplace=True)

    """ Assemble the prediction elements """
    if what == 'Today':
        c = concat_today(partitions)
        rtable = ptable[:-2]
        tphase = [partitions['findwatts'].index[0],
                  partitions['findwatts'].index[-1],
                  partitions['todaywatts'].index[0],
                  partitions['todaywatts'].index[-1]]
    elif what == 'Tomorrow':
        c = concat_tomorrow(partitions)
        rtable = ptable[-2:]
        tphase = [partitions['tomorrowwatts1'].index[0],
                  partitions['tomorrowwatts1'].index[0],
                  partitions['tomorrowwatts1'].index[0],
                  partitions['tomorrowwatts2'].index[-1]]
    elif what == 'Total':
        c = concat_total(partitions)
        rtable = ptable
        tphase = [partitions['findwatts'].index[0],
                  partitions['findwatts'].index[-1],
                  partitions['todaywatts'].index[0],
                  partitions['tomorrowwatts2'].index[-1]]

    time = np.array(list(c.index.values))
    smp, ivp1, ivp2, spph = c['SMP'], c['IVP1'], c['IVP2'], c['SPPH']
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB']

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<=0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
    sbpbdischarge[sbpb>0] = sbpb[sbpb>0]

        
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
            tphase
        ),
        get_kwh_line(
            time,
            smpon.cumsum()/1000/60 if smpon is not None else None,
            smpoff.cumsum()/1000/60 if smpoff is not None else None,
            ivp1.cumsum()/1000/60 if ivp1 is not None else None,
            ivp2.cumsum()/1000/60 if ivp2 is not None else None,
            spph.cumsum()/1000/60 if spph is not None else None,
            sbpi.cumsum()/1000/60 if sbpi is not None else None,
            sbpo.cumsum()/1000/60 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000/60 if sbpb is not None else None,
            sbpbdischarge.cumsum()/1000/60 if sbpb is not None else None,
            sbsb[0]*full_kwh+ (
                sbpbcharge.cumsum()/1000/60-
                sbpbdischarge.cumsum()/1000/60
            ),
            empty_kwh,
            full_kwh,
            price[logday[:2]],
            tphase))

    atable = pd.concat([rtable.iloc[:,:2],
                        rtable.iloc[:,2:].cumsum()], axis = 1)
    atable['START'] = "00:00"
    
    return {'what': what,
            'logday': logday,
            'w': w, 'kwh': kwh,
            'start': start, 'stop': stop,
            'predictdays': predictdays,
            'predicttables': [rtable, atable]}
