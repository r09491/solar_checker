import pathlib
import yaml
from aiohttp import web

BASE_DIR = pathlib.Path(__file__).parent.parent
config_path = BASE_DIR / 'conf' / 'main.yaml'

def get_conf(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config

conf = get_conf(config_path)

def setup_conf(app: web.Application):
    app['conf'] = conf

