__version__ = "0.0.0"
__author__ = "r09491@gmail.com"
__doc__="""
"""

import sys

from aiohttp import web

from settings import setup_conf
from jinja import setup_jinja2
from routes import setup_routes

def main() -> int:
    app = web.Application()
    setup_conf(app)
    setup_jinja2(app)
    setup_routes(app)
    web.run_app(app, host=app['conf']['host'], port=app['conf']['port'])
    return 0

if __name__ == '__main__':
    sys.exit(main())

