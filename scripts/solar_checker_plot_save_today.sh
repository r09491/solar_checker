#!/bin/bash -l

SOLAR_CHECKER=$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log
cat $SOLAR_CHECKER|solar_checker_plot_save.py --out_dir $SOLAR_CHECKER_STORE_DIR/images --price 0.369
