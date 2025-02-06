solar_checker_latest_once.py --iv_ip "apsystems" \
			     --sm_ip "tasmota" \
			     --sp_switch_4 "plug0" \
			     --sp_switch_3 "plug3" \
			     --sp_switch_2 "plug2" \
			     --sp_switch_1 "plug1" \
			     1> >(ssh r09491@pipi "cat >> 0WORK/solar_checker_latest_$(date +\%y\%m\%d).log") \
			     2> >(ssh r09491@pipi "cat >> 0WORK/solar_checker_error_$(date +\%y\%m\%d).log")
