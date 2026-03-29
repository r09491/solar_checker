#!/bin/bash -l


SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_zeroise_$(date +\%y\%m\%d).log
solar_checker_zeroise.py 2>> $SOLAR_CHECKER_ERROR &


