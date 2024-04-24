#!/bin/bash -l

SAMPLES=5
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n $SAMPLES $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug1 \
     --power_mean_import_open 10 \
     --power_mean_export_closed 5 \
     --power_samples $SAMPLES 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of low power devices. It
# starts the charging if power is exported after a certain period (11
# minutes).  It stops the charging if no power is exported to the
# provider after a certain period (11 minutes). At the end it shall
# ensure that the export is minimized.
