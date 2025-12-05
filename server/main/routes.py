from aiohttp import web
from settings import (
    HOME,
    BASE_DIR
)
from views import (
    plot_day,
    plot_month,
    plot_year,
    plot_predict,
    plot_predict_naive,
    plot_ai_cast,
    train_ai_cast,
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
    app.router.add_get('/plot_predict_naive', plot_predict_naive)
    app.router.add_get('/plot_predict_naive/{castday}', plot_predict_naive)
    app.router.add_get('/plot_ai_cast', plot_ai_cast)
    app.router.add_get('/plot_ai_cast/{castday}', plot_ai_cast)
    app.router.add_get('/train_ai_cast', train_ai_cast)

    
    app.router.add_static(
        '/static/',
        path= BASE_DIR / 'main' / 'static',
        name='static')

    app.add_routes(
        [
            web.static(
                '/solar_motion/',
                HOME / 'storage' / 'solar_motion',
                follow_symlinks=True
            )
        ]
    )
    
