#!/bin/bash -l


SOLAR_CHECKER_ERROR=$SOLAR_CHECKER_STORE_DIR/solar_checker_zeroise.log
solar_checker_zeroise.py 2>> $SOLAR_CHECKER_ERROR &


