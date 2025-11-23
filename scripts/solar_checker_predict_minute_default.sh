#!/bin/bash -l

M0=$(date -d "0 month" +\%m)
M1=$(date -d "1 month" +\%m)
SOLAR_CHECKER_LOGDAY=$(date -d "0 day ago" +\%y\%m\%d)
SOLAR_CHECKER_PREDICTWINDOW=7
SOLAR_CHECKER_PREFIX="solar_checker_latest"
SOLAR_CHECKER_STORE_DIR="/home/r09491/storage/solar_checker"
SOLAR_CHECKER_STARTTIME=$(date -d "3 hour ago" +\%H:\%M) 
SOLAR_CHECKER_STOPTIME=$(date +\%H:\%M) 
solar_checker_predict_minute.py \
    --logday $SOLAR_CHECKER_LOGDAY \
    --logpredictwindow $SOLAR_CHECKER_LOGPREDICTWIND \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --stoptime $SOLAR_CHECKER_STOPTIME \
    --predict True \
    --columns SBPI ## 2>/dev/null


