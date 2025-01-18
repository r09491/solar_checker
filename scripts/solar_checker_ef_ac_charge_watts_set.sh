#!/bin/bash -l

## Schedule example
##

## 1-59/8 * * * * sleep 20 && solar_checker_ac_charge_watts_set.sh
##

SAMPLES=1
SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
SMP=$(tail -n $SAMPLES $SOLAR_CHECKER_LATEST|gawk -F, '{print $2}')
ef_ac_charge_watts_balance_set.py --grid_watts $SMP  2>> $SOLAR_CHECKER_ERROR

# This script sets the charge rate in the Ecoflow Delta_Max to
# optimize storage of exceeding energy in a in a PV systems

