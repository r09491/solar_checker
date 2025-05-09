#!/bin/bash -l

SOLAR_CHECKER_TO_DAY=$(date -d "0 day" +\%y\%m\%d)
SOLAR_CHECKER_FROM_DAY="250507" ##$(date -d "1 day ago" +\%y\%m\%d)
SOLAR_CHECKER_PREFIX="solar_checker_latest"
./solar_checker_power_cast.py \
    --to_day $SOLAR_CHECKER_TO_DAY \
    --from_day $SOLAR_CHECKER_FROM_DAY \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR 


