#!/bin/bash -l

#TASMOTA=$SOLAR_CHECKER_STORE_DIR/tasmota_latest_$1.log
#APSYSTEMS=$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$1.log
#paste -d',' $TASMOTA $APSYSTEMS|solar_checker_plot.py --price 0.369
SOLAR_CHECKER=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$1.log
cat $SOLAR_CHECKER|solar_checker_slots.py --price 0.369


