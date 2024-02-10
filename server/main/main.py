__version__ = "0.0.1"
__author__ = "r09491@gmail.com"
__doc__="""
"""

import os
import sys

from aiohttp import web
import aiohttp_jinja2, jinja2

from routes import setup_routes
from settings import conf, BASE_DIR
from utils.samples import get_logdays

def get_logdays_jinja2():
    return get_logdays(conf['logprefix'], conf['logdir'])

def get_jinja2_loader() -> str:
    return jinja2.FileSystemLoader(str(BASE_DIR / 'main' / 'templates'))

def setup_jinja2(app: web.Application):
    loader = get_jinja2_loader()
    aiohttp_jinja2.setup(app, loader = loader )

    env = aiohttp_jinja2.get_env(app)
    env.globals.update(get_logdays_jinja2=get_logdays_jinja2)

    
def main() -> int:
    app = web.Application()
    setup_routes(app)
    setup_jinja2(app)
    app['conf'] = conf    
    web.run_app(app, host=conf['host'], port=conf['port'])
    return 0

if __name__ == '__main__':
    sys.exit(main())

