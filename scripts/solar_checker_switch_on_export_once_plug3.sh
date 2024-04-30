#!/bin/bash -l

SAMPLES=5
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n $SAMPLES $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug3 \
     --power_mean_import_open 10 \
     --power_mean_export_closed 200 \
     --power_samples $SAMPLES 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of my ecoflow. Asumed charge rate 200!
