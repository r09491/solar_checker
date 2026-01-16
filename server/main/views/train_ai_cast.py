import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

from aiohttp import web
import aiohttp_jinja2

@aiohttp_jinja2.template('train_ai_cast.html')
async def train_ai_cast(request: web.Request) -> dict:

    return aiohttp_jinja2.render_template(
        'error.html', request,
        {'error' : 'AI training is not implemented.\nUse script from command line!'}
    )
