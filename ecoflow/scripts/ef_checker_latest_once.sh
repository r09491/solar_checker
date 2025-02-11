## CRONTAB (Adapt as necesssary)
#SHELL=/bin/bash
#PATH=/home/r09491/7WORK-3.12/.v3.12/bin:/usr/bin:/bin
#EF_CHECKER_STORE_DIR=/media/xfer/fish/ecoflow_checker
#
#
## Record the latest power of the smartmeter and inverter
#*/5 * * * * ef_checker_latest.sh

ef_checker_latest_once.py >> \
	 $ECOFLOW_CHECKER_STORE_DIR/ecoflow_checker_latest_$(date +\%y\%m\%d).log 2>> \
	 $ECOFLOW_CHECKER_STORE_DIR/ecoflow_checker_error_$(date +\%y\%m\%d).log

