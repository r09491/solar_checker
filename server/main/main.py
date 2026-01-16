__version__ = "0.0.0"
__author__ = "r09491@gmail.com"
__doc__=""" Starts the web server
"""

import sys
import os.path
import argparse

from aiohttp import web

from settings import setup_conf
from jinja import setup_jinja2
from routes import setup_routes

from dataclasses import dataclass

@dataclass
class Config_Args:
    config_path: str

def parse_args() -> Config_Arguments:
    """Parse command line arguments"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Get the latest weather forecast',
        epilog=__doc__)

    parser.add_argument('--version', action = 'version', version = __version__)

    parser.add_argument(
        '--config_path', type=str, required=True,
        help = "The path of the YAML file to configure the server!")

    args = parser.parse_args()
    
    return Config_Args(
        args.config_path if os.path.isfile(
            args.config_path
        ) else None
    )
        
    

def main() -> int:
    args = parse_args()
    if args.config_path is None:
        print(f'The config file path is missing or wrong.')
        return -1

    app = web.Application()
    setup_conf(app, args.config_path)
    setup_jinja2(app)
    setup_routes(app)
    web.run_app(app, host=app['conf']['host'], port=app['conf']['port'])
    return 0

if __name__ == '__main__':
    sys.exit(main())

