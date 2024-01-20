# To run in interactive shells SOLAR_CHECKER_STORE_DIR is defined in '.bashrc'
# (P = Power, EN = Energy current Day, EL = Energy Lifetime)
alias apsystems_latest_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
  awk -F',' 'BEGIN{price=0.369}{printf(\"P %03.0f+%03.0f=%03.0fW  ED %.3f+%.3f=%.3fkWh|%.2f€  EL %.1f+%.1f=%.1fkWh|%.2f€\n\", \$4,\$7,\$4+\$7, \$5,\$8,\$5+\$8,(\$5+\$8)*price, \$6, \$9, \$6+\$9, (\$6+\$9)*price)}'"

alias apsystems_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
          awk -F',' '{printf(\"%d,%f,%f\n\", NR, \$4, \$7)}' | \
	  termgraph --color {green,cyan} --stacked --suffix 'W' \
	  --title 'Apsystems Inverter Watts (Channel 1, Channel 2)'"

alias apsystems_watt_hours="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f,%.3f\n\", NR, \$5, \$8)}' | \
			    termgraph --color {green,cyan} --stacked --suffix 'kWh' \
			    	      --title 'Apsystems Inverter Watt-Hours (Channel 1,Channel 2)'"

alias apsystems_watt_hours_lifetime="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f,%.3f\n\", NR, \$6, \$9)}' | \
			    termgraph --color {green,cyan} --stacked --suffix 'kWh' \
			    	      --title 'Apsystems Inverter Lifetime Watt-Hours (Channel 1,Channel 2)'"


#based on the energy at the start of the year (P = Power, EY = Energy current Year, EL = Energy Lifetime)
alias tasmota_latest_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log| \
    awk -F',' 'BEGIN{start=4192;price=0.369}{printf(\"P %04.0fW  EY %.1fkWh|%.2f€ EL %.1fkWh|%.2f€\n\",\$2, \$3-start, (\$3-start)*price, \$3, \$3*price)}'"

alias tasmota_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%f\n\", NR, \$2)}' | \
			    termgraph --suffix 'W' \
			    	      --title 'Tasmota Smartmeter Watts'"

alias tasmota_watt_hours_lifetime="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f\n\", NR, \$3/1000)}' | \
			    termgraph --suffix 'kWh' \
			    	      --title 'Tasmota Smartmeter Lifetime Watt-Hours'"

alias solar_checker_plot="solar_checker_plot.sh"
alias solar_checker_plot_anyday="solar_checker_plot_anyday.sh"
alias solar_checker_plot_yesterday="solar_checker_plot_yesterday.sh"
alias solar_checker_slots="solar_checker_slots.sh"
alias solar_checker_slots_anyday="solar_checker_slots_anyday.sh"
alias solar_checker_slots_yesterday="solar_checker_slots_yesterday.sh"

