from aiohttp import web
from views import plot_power
from settings import BASE_DIR

def setup_routes(app: web.Application):
    app.router.add_get('/', plot_power)
    app.router.add_get('/plot_power', plot_power)
    app.router.add_get('/plot_power/{logday}', plot_power)
    
    app.router.add_static('/static/',
                          path= BASE_DIR / 'main' / 'static',
                          name='static')
