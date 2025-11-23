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

from datetime import(
    datetime,
    timedelta
)
from utils.common import (
    ym_1_month_ago,
    ym_1_month_ahead,
    ym_12_month_ago,
    ym_12_month_ahead
)
from utils.samples import (
    get_kwh_sum_month_unified
)
from utils.plots import (
    get_kwh_bar_unified
)

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
    if umkwh is None:
        return aiohttp_jinja2.render_template('error.html', request,
            {'error' : f"No valid logfile found for month '{logmonth}'"})

    umplot  = await get_kwh_bar_unified(
        *umkwh.values(), price[logmonth[:2]], 0.7, '%d%n%a')

    logger.info(f'{__me__}: done')
    return {'logmonth': logmonth,
            'log1monthago': ym_1_month_ago(logmonth),
            'log1monthahead': ym_1_month_ahead(logmonth),
            'log12monthago': ym_12_month_ago(logmonth),
            'log12monthahead': ym_12_month_ahead(logmonth),
            'kwh': umplot}
