### OBSOLETE

## CRONTAB (Adapt as necesssary)
#SHELL=/bin/bash
#PATH=/home/r09491/7WORK-3.12/.v3.12/bin:/usr/bin:/bin
#SOLAR_CHECKER_STORE_DIR=/media/xfer/fish/solar_checker
#
#
## Record the latest power of the smartmeter and inverter
#*/5 * * * * tasmota_latest_get_cron.sh && apsystems_latest_get_cron.sh

apsystems_latest_get.py --ip "192.168.101.48" >> \
			$SOLAR_CHECKER_STORE_DIR/apsystems_latest_$(date +\%y\%m\%d).log 2>> \
			$SOLAR_CHECKER_STORE_DIR/error.log

