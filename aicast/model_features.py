TIME_FEATURES = [
    'hour',
#    'minute',
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
    'cloud_cover',
    'temperature',
    'dew_point',
    'visibility'
]

## !!! Add lags and rolls to the train pool manually !!!

SBPI_FEATURES = TIME_FEATURES + POSITION_FEATURES + WEATHER_FEATURES
SBPI_FEATURES_lags = [1,2]
SBPI_FEATURES_rolls = []

SBSB_FEATURES = TIME_FEATURES + ['SBPI'] 
SBSB_FEATURES_lags = [1]
SBSB_FEATURES_rolls= []

SBPB_FEATURES = TIME_FEATURES + ['SBPI','SBSB']
SBPB_FEATURES_lags = [1,2] 
SBPB_FEATURES_rolls= []

SMP_FEATURES = TIME_FEATURES + ['SBPO']
SMP_FEATURES_lags = [1,2,3]
SMP_FEATURES_rolls = [2]
