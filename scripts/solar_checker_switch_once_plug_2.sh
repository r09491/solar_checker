#!/bin/bash -l

SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n 10 $SOLAR_CHECKER_LATEST|solar_checker_switch_once.py \
     --plug_name plug2 \
     --power_mean_open 350 \
     --power_mean_closed 400 2>> $SOLAR_CHECKER_ERROR



