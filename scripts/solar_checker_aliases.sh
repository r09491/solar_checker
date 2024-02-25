# To run in interactive shells SOLAR_CHECKER_STORE_DIR is defined in '.bashrc'
# (PI = Power, EN = Energy current Day, EL = Energy Lifetime)
alias apsystems_latest_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
  awk -F',' 'BEGIN{price=0.369}{printf(\"PI %03.0f+%03.0f=%03.0fW  ED %.3f+%.3f=%.3fkWh|%.2f€  EL %.1f+%.1f=%.1fkWh|%.2f€\n\", \$4,\$7,\$4+\$7, \$5,\$8,\$5+\$8,(\$5+\$8)*price, \$6, \$9, \$6+\$9, (\$6+\$9)*price)}'"

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


#based on the energy at the start of the year (PH = Power, EY = Energy current Year, EL = Energy Lifetime)
alias tasmota_latest_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log| \
    awk -F',' 'BEGIN{start=4192;price=0.369}{printf(\"PH %04.0fW  EY %.1fkWh|%.2f€ EL %.1fkWh|%.2f€\n\",\$2, \$3-start, (\$3-start)*price, \$3, \$3*price)}'"

alias tasmota_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%f\n\", NR, \$2)}' | \
			    termgraph --suffix 'W' \
			    	      --title 'Tasmota Smartmeter Watts'"

alias tasmota_watt_hours_lifetime="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{ printf(\"%d,%.3f\n\", NR, \$3/1000)}' | \
			    termgraph --suffix 'kWh' \
			    	      --title 'Tasmota Smartmeter Lifetime Watt-Hours'"


alias tuya_latest_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log| \
    awk -F',' 'BEGIN{}{printf(\"PP %03.0fW\n\",\$10)}'"

alias tuya_watts="tail -n 5 \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
      			    awk -F',' '{printf(\"%d,%.3f\n\", NR, \$10)}' | \
			    termgraph --suffix 'W' --title 'Tuya Smartplug Watts'"

# (PI = Power Inverter, PP = Power Plug, PH = Power Home)
alias solar_checker_watts_tail="tail -f \$SOLAR_CHECKER_STORE_DIR/solar_checker_latest_\$(date +%y%m%d).log | \
  awk -F',' '{printf(\"%s PR %03.0fW PO %03.0fW PB %03.0fW  PI %03.0f+%03.0f=%03.0fW  PP %03.0fW  PH %04.0fW\n\", \$1, \$11, \$12, \$13, \$4,\$7,\$4+\$7, \$10, \$2)}'"

alias solar_checker_plot="solar_checker_plot.sh"
alias solar_checker_plot_anyday="solar_checker_plot_anyday.sh"
alias solar_checker_plot_yesterday="solar_checker_plot_yesterday.sh"
alias solar_checker_slots="solar_checker_slots.sh"
alias solar_checker_slots_anyday="solar_checker_slots_anyday.sh"
alias solar_checker_slots_yesterday="solar_checker_slots_yesterday.sh"

