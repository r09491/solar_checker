#!/bin/bash -l

TASMOTA=$SOLAR_CHECKER_STORE_DIR/tasmota_latest_$(date +\%y\%m\%d).log
APSYSTEMS=$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$(date +\%y\%m\%d).log
paste -d',' $TASMOTA $APSYSTEMS|solar_checker_slots.py

