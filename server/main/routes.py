from aiohttp import web
from settings import BASE_DIR
from views import (
    plot_day,
    plot_month,
    plot_year,
    plot_predict,
    plot_ai_predict,
    start_ai_train
)

def setup_routes(app: web.Application):
    app.router.add_get('/', plot_day)
    app.router.add_get('/plot_day', plot_day)
    app.router.add_get('/plot_day/{logday}', plot_day)
    app.router.add_get('/plot_month', plot_month)
    app.router.add_get('/plot_month/{logmonth}', plot_month)
    app.router.add_get('/plot_year', plot_year)
    app.router.add_get('/plot_year/{logyear}', plot_year)
    app.router.add_get('/plot_predict/{logday}/{what}', plot_predict)
    app.router.add_get('/plot_ai_predict', plot_ai_predict)
    app.router.add_get('/plot_ai_predict/{castday}', plot_ai_predict)
    app.router.add_get('/start_ai_train', start_ai_train)
    
    app.router.add_static('/static/',
                          path= BASE_DIR / 'main' / 'static',
                          name='static')
