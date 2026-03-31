#!/bin/bash -l


SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_zeroise_error_$(date +\%y\%m\%d).log
SOLAR_CHECKER_LATEST=$SOLAR_CHECKER_STORE_DIR/solar_checker_zeroise_latest_$(date +\%y\%m\%d).log
solar_checker_zeroise.py 2>>$SOLAR_CHECKER_ERROR 1>>$SOLAR_CHECKER_LATEST


