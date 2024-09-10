#!/bin/bash -l

SOLAR_CHECKER_PREFIX="solar_checker_latest"
SOLAR_CHECKER_FORMAT="24[0,0][8,9]*"
SOLAR_CHECKER_TODAY=$(date +\%y\%m\%d)
SOLAR_CHECKER_START_TIME=$(date -d "3 hour ago" +\%H:\%M) 
SOLAR_CHECKER_STOP_TIME=$(date +\%H:\%M) 
solar_checker_closest_find.py \
    --logday $SOLAR_CHECKER_TODAY \
    --logdayformat $SOLAR_CHECKER_FORMAT \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --start_time $SOLAR_CHECKER_START_TIME \
    --stop_time $SOLAR_CHECKER_STOP_TIME \
    --column $1 2>/dev/null


# Find the closest logfiles to the today'slogfile using samples of the last hours
