## CRONTAB (Adapt as necesssary)
#SHELL=/bin/bash
#PATH=/home/r09491/7WORK-3.12/.v3.12/bin:/usr/bin:/bin
#SOLAR_CHECKER_STORE_DIR=/media/xfer/fish/solar_checker
#
#
## Record the latest power of the smartmeter and inverter
#*/5 * * * * solar_checker_latest.sh

solar_checker_latest_once.py --iv_ip "192.168.101.48" --sm_ip "192.168.101.30" --sp_name "plug1" >> \
			$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_$(date +\%y\%m\%d).log 2>> \
			$SOLAR_CHECKER_STORE_DIR/solar_checker_error_$(date +\%y\%m\%d).log

