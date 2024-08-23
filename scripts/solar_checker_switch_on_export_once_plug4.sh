#!/bin/bash -l

## Schedule example
##
## ## Needs a few minutes to settle
## 0-59/4 * * * * sleep 40 && solar_checker_home_load_set_once.sh
## ##
## 1-59/8 * * * * sleep 20 && solar_checker_switch_on_export_once_plug4.sh
## 3-59/8 * * * * sleep 20 && solar_checker_switch_on_export_once_plug3.sh
## 5-59/8 * * * * sleep 20 && solar_checker_switch_on_export_once_plug2.sh
## 7-59/8 * * * * sleep 20 && solar_checker_switch_on_export_once_plug1.sh
##

SAMPLES=2
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n $SAMPLES $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug0 \
     --power_mean_import_open 50 \
     --power_mean_export_closed 10 \
     --power_samples $SAMPLES 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of devices with priority
