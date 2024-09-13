#!/bin/bash -l

SOLAR_CHECKER_PREFIX="solar_checker_latest"
SOLAR_CHECKER_LOGFORMAT="24[0,0][8,9]*"
SOLAR_CHECKER_LOGDAY=$(date -d "0 day ago" +\%y\%m\%d)
#SOLAR_CHECKER_START_TIME=$(date -d "3 hour ago" +\%H:\%M) 
SOLAR_CHECKER_STOP_TIME=$(date +\%H:\%M) 
solar_checker_closest_find.py \
    --logday $SOLAR_CHECKER_LOGDAY \
    --logdayformat $SOLAR_CHECKER_LOGFORMAT \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --stop_time $SOLAR_CHECKER_STOP_TIME \
    --column $1


# Find the closest logfiles to the today'slogfile using samples of the last hours
