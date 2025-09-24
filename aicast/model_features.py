TIME_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year'
]

POSITION_FEATURES = [
    'azimuth',
    'elevation',
    'is_daylight',
    'can_see_sun'
]

WEATHER_FEATURES = [
    'sunshine',
    'cloud_cover',
    'temperature',
    'dew_point',
    'visibility'
]

## !!! Add lags and rolls to the train pool manually !!!

SBPI_FEATURES = TIME_FEATURES + POSITION_FEATURES + WEATHER_FEATURES
SBPI_FEATURES_lags = [1,2,3]
SBPI_FEATURES_rolls = []

SBSB_FEATURES = TIME_FEATURES + WEATHER_FEATURES + ['SBPI', 'SBPI_below_40', 'SBPI_above_100']
SBSB_FEATURES_lags = [1,2,3]
SBSB_FEATURES_rolls= [720,1440]

SBPB_FEATURES = TIME_FEATURES + ['SBPI','SBPI_below_40','SBPI_above_100','SBSB','SBSB_is_empty','SBSB_almost_full','SBSB_is_full']
SBPB_FEATURES_lags = [1,2,3] 
SBPB_FEATURES_rolls= []

SMP_FEATURES = TIME_FEATURES + ['SBPI','SBSB','SBSB_is_empty','SBSB_almost_full','SBSB_is_full','SBPB_is_charge', 'SBPO']
SMP_FEATURES_lags = [1,2,3]
SMP_FEATURES_rolls = [4]
