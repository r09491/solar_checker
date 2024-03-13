#!/bin/bash -l

SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n 17 $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug2 \
     --power_mean_import_open 250 \
     --power_mean_export_closed 100 \
     --power_mean_deviation 10 \
     --power_samples 17 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of ecoflow powerstation. It
# is assumed that the charge rate is set to 200W

