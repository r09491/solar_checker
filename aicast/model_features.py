SBPI_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'sunshine',
    'cloud_cover',
    'temperature',
    'dew_point',
    'visibility'
]

SBPB_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI'
]

SMP_lag1_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO'
]

SMP_lag2_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO',
    'SMP_lag1'
]


SMP_roll5_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO',
    'SMP_lag1',
    'SMP_lag2'
]

SMP_roll10_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO',
    'SMP_lag1',
    'SMP_lag2',
    'SMP_roll5'    
]

SMP_roll20_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO',
    'SMP_lag1',
    'SMP_lag2',
    'SMP_roll5',
    'SMP_roll10'
]

SMP_FEATURES = [
    'hour',
    'minute',
    'month',
    'year',
    'day_of_year',
    'is_daylight',
    'SBPI',
    'SBPB',
    'SBPO',
    'SMP_lag1',
    'SMP_lag2',
    'SMP_roll5',
    'SMP_roll10',
    'SMP_roll20'
]
