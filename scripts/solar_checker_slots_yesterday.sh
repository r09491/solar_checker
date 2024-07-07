#!/bin/bash -l

#TASMOTA=$SOLAR_CHECKER_STORE_DIR/tasmota_latest_$(date -d "yesterday" +\%y\%m\%d).log
#APSYSTEMS=$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$(date -d "yesterday" +\%y\%m\%d).log
#paste -d',' $TASMOTA $APSYSTEMS|solar_checker_slots.py
SOLAR_CHECKER=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date -d "yesterday" +\%y\%m\%d).log
cat $SOLAR_CHECKER|solar_checker_slots.py


