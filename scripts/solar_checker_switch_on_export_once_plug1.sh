#!/bin/bash -l

SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n 11 $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug1 \
     --power_mean_import_open 20 \
     --power_mean_export_closed 20 \
     --power_mean_deviation 11 \
     --power_samples 13 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of low power devices. It
# starts the charging if power is exported after a certain period (13
# minutes).  It stops the charging if no power is exported to the
# provider after a certain period (13 minutes). At the end it shall
# ensure that the export is minimized.
