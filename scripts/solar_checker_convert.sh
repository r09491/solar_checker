#!/bin/bash -l

#SOLAR_CHECKER_LOGFORMAT="??????"
SOLAR_CHECKER_LOGDAY="250512"
SOLAR_CHECKER_PREFIX="solar_checker_latest"
./solar_checker_convert.py \
    --logday $SOLAR_CHECKER_LOGDAY \
    --logprefix $SOLAR_CHECKER_PREFIX \
    --logdir $SOLAR_CHECKER_STORE_DIR 
