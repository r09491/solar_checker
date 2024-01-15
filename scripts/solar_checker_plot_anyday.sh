#!/bin/bash -l

TASMOTA=$SOLAR_CHECKER_STORE_DIR/tasmota_latest_$1.log
APSYSTEMS=$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$1.log
paste -d',' $TASMOTA $APSYSTEMS|solar_checker_plot.py --price 0.369


