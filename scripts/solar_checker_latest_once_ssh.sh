
#*/4 * * * * solar_checker_latest_once_ssh.sh

solar_checker_latest_once.py --iv_ip "192.168.101.48" \
			     --sm_ip "192.168.101.30" \
			     --sp_switch_4 "plug0" \
			     --sp_switch_3 "plug3" \
			     --sp_switch_2 "plug2" \
			     --sp_switch_1 "plug1" \
			     2> >(ssh r09491@wanderer "cat >> storage/solar_checker/solar_checker_error_$(date +\%y\%m\%d).log") \
			     > >(ssh r09491@wanderer "cat >> storage/solar_checker/solar_checker_latest_$(date +\%y\%m\%d).log")

