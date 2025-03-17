#!/bin/bash -l


SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
cat $SOLAR_CHECKER_LATEST|solar_checker_plug_switch_once.py \
     --plug_name plug0 2>> $SOLAR_CHECKER_ERROR

# This script shall start/stop the charging of devices with low power, eg smartphones


