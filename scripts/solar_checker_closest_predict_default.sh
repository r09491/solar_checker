#!/bin/bash -l

SOLAR_CHECKER_PREFIX="solar_checker_latest"
SOLAR_CHECKER_LOGFORMAT="24*"
SOLAR_CHECKER_LOGDAY=$(date -d "0 day ago" +\%y\%m\%d)
#SOLAR_CHECKER_STARTTIME=$(date -d "3 hour ago" +\%H:\%M) 
SOLAR_CHECKER_STOPTIME=$(date +\%H:\%M) 
solar_checker_closest_predict.py \
    --logday $SOLAR_CHECKER_LOGDAY \
    --logdayformat $SOLAR_CHECKER_LOGFORMAT \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --stoptime $SOLAR_CHECKER_STOPTIME \
    --predict True \
    --column SBPI 2>/dev/null


