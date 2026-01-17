from aiohttp import web
import aiohttp_jinja2, jinja2

from settings import BASE_DIR
from utils.csvlog import _get_logdays

conf = None
def get_logdays_jinja2():
    """ !!!  Coroutines can not be used in templates !!! """
    return set(_get_logdays(conf['logprefix'], conf['logdir']))

def get_logmonths_jinja2():
    logdays = get_logdays_jinja2()
    return set(ld[:-2] for ld in logdays)

def get_logyears_jinja2():
    logdays = get_logdays_jinja2()
    return set(ld[:2] for ld in logdays)


def get_remote_access_jinja2():
    return conf['name'], conf['remote_host'], conf['remote_port'], conf['side']

def get_other_access_jinja2():
    return conf['other_name'], conf['other_host'], conf['other_port']


def get_jinja2_loader() -> str:
    return jinja2.FileSystemLoader(str(BASE_DIR / 'main' / 'templates'))

def setup_jinja2(app: web.Application):
    global conf
    conf = app['conf']
    
    loader = get_jinja2_loader()
    aiohttp_jinja2.setup(app, loader = loader )

    env = aiohttp_jinja2.get_env(app)
    env.globals.update(get_logdays_jinja2=get_logdays_jinja2)
    env.globals.update(get_logmonths_jinja2=get_logmonths_jinja2)
    env.globals.update(get_logyears_jinja2=get_logyears_jinja2)
    env.globals.update(get_remote_access_jinja2=get_remote_access_jinja2)
    env.globals.update(get_other_access_jinja2=get_other_access_jinja2)
