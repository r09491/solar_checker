from aiohttp import web
import aiohttp_jinja2, jinja2

from settings import conf, BASE_DIR
from utils.samples import _get_logdays

def get_logdays_jinja2():
    """ !!!  Coroutines can not be used in templates !!! """
    return set(_get_logdays(conf['logprefix'], conf['logdir']))

def get_logmonths_jinja2():
    logdays = get_logdays_jinja2()
    return set(ld[:-2] for ld in logdays)

def get_logyears_jinja2():
    logdays = get_logdays_jinja2()
    return set(ld[:2] for ld in logdays)


def get_jinja2_loader() -> str:
    return jinja2.FileSystemLoader(str(BASE_DIR / 'main' / 'templates'))

def setup_jinja2(app: web.Application):
    loader = get_jinja2_loader()
    aiohttp_jinja2.setup(app, loader = loader )

    env = aiohttp_jinja2.get_env(app)
    env.globals.update(get_logdays_jinja2=get_logdays_jinja2)
    env.globals.update(get_logmonths_jinja2=get_logmonths_jinja2)
    env.globals.update(get_logyears_jinja2=get_logyears_jinja2)
