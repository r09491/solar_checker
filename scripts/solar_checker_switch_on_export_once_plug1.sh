#!/bin/bash -l

## Schedule example
##
## # Record the latest power of the smartmeter and inverter
## # OBSOLETE * * * * * tasmota_latest_get_cron.sh && apsystems_latest_get_cron.sh
## * * * * * solar_checker_latest_once.sh
##
## ## Needs a few minutes to settle
## 0-59/4 * * * * sleep 40 && solar_checker_home_load_set_once.sh
## ##
## 1-59/4 * * * * sleep 20 && solar_checker_switch_on_export_once_plug4.sh
## 2-59/4 * * * * sleep 20 && solar_checker_switch_on_export_once_plug3.sh
## 3-59/4 * * * * sleep 20 && solar_checker_switch_on_export_once_plug2.sh
## 4-59/4 * * * * sleep 20 && solar_checker_switch_on_export_once_plug1.sh
##

SAMPLES=2
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
tail -n $SAMPLES $SOLAR_CHECKER_LATEST|solar_checker_switch_on_export_once.py \
     --plug_name plug1 \
     --power_mean_import_open 15 \
     --power_mean_export_closed 5 \
     --power_samples $SAMPLES 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of low power devices. It
# starts the charging if power is exported after a certain period (11
# minutes).  It stops the charging if no power is exported to the
# provider after a certain period (11 minutes). At the end it shall
# ensure that the export is minimized.
