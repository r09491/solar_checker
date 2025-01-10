#!/bin/bash -l

#SOLAR_CHECKER_LOGFORMAT="24[01][34567890]??"
SOLAR_CHECKER_LOGFORMAT="241026"
SOLAR_CHECKER_PREFIX="solar_checker_latest"
./solar_checker_convert.py \
    --logdayformat $SOLAR_CHECKER_LOGFORMAT \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR 
