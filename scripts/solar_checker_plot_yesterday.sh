#!/bin/bash -l

TASMOTA=$SOLAR_CHECKER_STORE_DIR/tasmota_latest_$(date -d "yesterday" +\%y\%m\%d).log
APSYSTEMS=$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$(date -d "yesterday" +\%y\%m\%d).log
paste -d',' $TASMOTA $APSYSTEMS|./solar_checker_plot.py --price 0.369


