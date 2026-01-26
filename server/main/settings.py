import pathlib
import yaml
from aiohttp import web

HOME = pathlib.Path.home()
BASE_DIR = pathlib.Path(__file__).parent.parent

def get_conf(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config

def setup_conf(
        app: web.Application,
        config_path: str
):
    app['conf'] = get_conf(config_path)

