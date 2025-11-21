#!/bin/bash -l

M0=$(date -d "0 month" +\%m)
M1=$(date -d "1 month" +\%m)
SOLAR_CHECKER_LOGMAXDAYS=7
SOLAR_CHECKER_LOGFORMAT="??[${M0:0:1}${M1:0:1}][${M0:1:1}${M1:1:1}]??"
SOLAR_CHECKER_PREFIX="solar_checker_latest"
SOLAR_CHECKER_LOGDAY=$(date -d "0 day ago" +\%y\%m\%d)
SOLAR_CHECKER_STARTTIME=$(date -d "2 hour ago" +\%H:\%M) 
SOLAR_CHECKER_STOPTIME=$(date +\%H:\%M) 
solar_checker_predict_minute.py \
    --logday $SOLAR_CHECKER_LOGDAY \
    --logdayformat $SOLAR_CHECKER_LOGFORMAT \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --stoptime $SOLAR_CHECKER_STOPTIME \
    --starttime $SOLAR_CHECKER_STARTTIME \
    --predict True \
    --columns $1 2>/dev/null


# Find the closest logfiles to the today'slogfile using samples of the last hours
