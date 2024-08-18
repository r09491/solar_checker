#!/bin/bash -l

## Schedule example
##
## # Record the latest power of the smartmeter and inverter
## # OBSOLETE * * * * * tasmota_latest_get_cron.sh && apsystems_latest_get_cron.sh
## * * * * * solar_checker_latest_once.sh
##
## ## Needs a few minutes to settle
## 0-59/5 * * * * sleep 30 && solar_checker_home_load_set_once.sh
## ##
## 1-59/5 * * * * sleep 30 && solar_checker_switch_on_export_once_plug4.sh
## 2-59/5 * * * * sleep 30 && solar_checker_switch_on_export_once_plug3.sh
## 3-59/5 * * * * sleep 30 && solar_checker_switch_on_export_once_plug2.sh
## 4-59/5 * * * * sleep 30 && solar_checker_switch_on_export_once_plug1.sh
##

SAMPLES=3
ssh r09491@wanderer "tail -n storage/solar_checker/solar_checker_latest_$(date +\%y\%m\%d).log" | \
    solar_checker_home_load_set_once.py \
	--power_samples $SAMPLES \
	2> >(ssh r09491@wanderer "cat >> storage/solar_checker/solar_checker_error_$(date +\%y\%m\%d).log")



