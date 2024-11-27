#!/bin/bash -l

solar_checker_plot_save.py \
    --logday $(date +\%y\%m\%d) \
    --logprefix "solar_checker_latest" \
    --logdir $SOLAR_CHECKER_STORE_DIR \
    --outdir $SOLAR_CHECKER_STORE_DIR/images \
    --price 0.369
