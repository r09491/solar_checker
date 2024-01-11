# To run in interactive shells SOLAR_CHECKER_STORE_DIR is defined in '.bashrc'

alias tail_apsystems_latest="tail -f \$SOLAR_CHECKER_STORE_DIR/apsystems_latest_\$(date +%y%m%d).log | \
  awk -F',' '{printf(\"P %03.0f/%03.0f %03.0f W  E %.3f/%.3f %.3f kWh  T %.1f/%.1f %.1f kWh\n\", \$1, \$4, \$1+\$4, \$2, \$5, \$2+\$5, \$3, \$6, \$3+\$6)}'"

alias apsystems_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/apsystems_latest_\$(date +%y%m%d).log | \
          awk -F',' '{printf(\"%d,%f,%f\n\", NR, \$1, \$4)}' | \
	  termgraph --color {green,cyan} --stacked --suffix 'W' \
	  --title 'Apsystems Inverter Watts (Channel 1, Channel 2)'"

alias apsystems_watt_hours="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/apsystems_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f,%.3f\n\", NR, \$2, \$5)}' | \
			    termgraph --color {green,cyan} --stacked --suffix 'kWh' \
			    	      --title 'Apsystems Inverter Watt-Hours (Channel 1,Channel 2)'"

alias apsystems_watt_hours_lifetime="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/apsystems_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f,%.3f\n\", NR, \$3, \$6)}' | \
			    termgraph --color {green,cyan} --stacked --suffix 'kWh' \
			    	      --title 'Apsystems Inverter Lifetime Watt-Hours (Channel 1,Channel 2)'"

alias tail_tasmota_latest="tail -f \$SOLAR_CHECKER_STORE_DIR/tasmota_latest_\$(date +%y%m%d).log| \
    awk -F',' '{ printf(\"P %04.0f W  T %.1f kWh\n\",\$2, \$3)}'"


alias tasmota_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/tasmota_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%f\n\", NR, \$2)}' | \
			    termgraph --suffix 'W' \
			    	      --title 'Tasmota Smartmeter Watts'"

alias tasmotawatt_hours_lifetime="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/tasmota_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f\n\", NR, \$3/1000)}' | \
			    termgraph --suffix 'kWh' \
			    	      --title 'Tasmota Smartmeter Lifetime Watt-Hours'"

alias solar_checker_plot="solar_checker_plot.sh"
alias solar_checker_plot_yesterday="solar_checker_plot_yesterday.sh"

