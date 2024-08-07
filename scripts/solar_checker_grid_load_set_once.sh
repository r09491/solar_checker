#!/bin/bash -l

SAMPLES=5
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n $SAMPLES $SOLAR_CHECKER_LATEST|solar_checker_grid_load_set_once.py \
     --serial_number "AZV6Y60D33200788" \
     --power_samples $SAMPLES
##2>> $SOLAR_CHECKER_ERROR


