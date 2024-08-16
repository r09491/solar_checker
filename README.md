# Solar Checker -  Python Library

## Overview

The Solar Checker Python library provides APIs for the APsystems EZ1
microinverter, Tasmota smartmeter, a poor Tuya library for
smartplugs, a poor Anker library for the Solix solarbank. Based on
these four APIs there are scripts to record their latest power data
which in turn can be used for plots to visualise them.

After some time a HTTP server was created for displaying the recorded
data. It facilitates the process to monitor my solar power station and
to assess if it will pay off at a point of time.

Again after some time the Anker API was extended for setting the home
load power with the intention to minimize the output delivered from
the solarbank to the power grid.

The following example is the output of a log day on the HTTP
server. It shows the components with the power flow for my system.

![alt text](images/solar_checker_logday.png)

---

## Setup your Inverter

The local API access needs to be activated once in the settings of the APsystems Easy Power App. 
<ul>
<li>Step 1: Connect to the inverter using the "Direct Connection" method.</li>
<li>Step 2: Establish a connection with your inverter.</li>
<li>Step 3: Select the Settings menu.</li>
<li>Step 4: Switch to the "Local Mode" section.</li>
<li>Step 5: Activate local mode and select "Continuous"</li>
<li>Step 6: By some magic the inverter will be added to your Homenet. It runs an HTTP server on port 8050</li>
</ul>

---

## Setup Tasmota for your Smartmeter

There are a lot of tutorials on how to setup Tasmota for a smartmeter
on the internet.

---

## Setup Poortuya for your Smartplug

Install the 'tinytuya' package and run the magic 'python3 -m tinytuya
scan'. Follow the interesting instructions in that repository!

These will produce some json files to be used to setup the config file
'.poortuya'. There is a tepmplate in the directory 'poortuya'.

Ensure you have a proper '.poortuya' is in your home directory!

---

## Setup Pooranker for your Solarbank

Install the anker-solix-api [repositiory](https://github.com/thomluther/anker-solix-api)

if you want to install on a Raspberry with Python 3.7 clone the
[fork](https://github.com/r09491/anker-solix-api.git) and run ''pip3
install .'

## Installation

I installed the 'apsystems', the 'tosmota' 'pooranker' and the
'poortuya' APIs on a standard raspberry buster system with python
version 3.7.3. In order to use the scripts the python3-numpy,
python3-pandas, python3-matplotlib packages have to be installed with
'apt' in advance. I used 'sudo' for a system wide install avoiding to
deal with local paths and local pip libraries in cron. You might have
a different philosophy and use virtual environments.
It should be installable on any Linux with python >= 3.7.1.

I installed the repository also under 'termux' on my Android
smartphone.

<ul>
<li>Step 1: git clone the repository</li>
<li>Step 2: cd to the directory solar_checker</li>
<li>Step 3: install with pip</li>
</ul>

```bash
git clone https://github.com/r09491/solar_checker.git
cd solar_checker
sudo pip3 install .
```

For the recording in the script 'solar_checker_latest_once.sh' adapt
the ip addresses and add it to 'cron'. Be sure to have the 'PATH and
'SOLAR_CHECKER_STORE_DIR* environment variables set as documented in
the script!

---

## Examples

The following examples show the setting of the maximum power limit of
the APsystem EZ1 micro inverter. Be advised that there might be
restrictions covered by national laws. Especially in Germany the
maximum power limit is still 600W.

Currently the sun is not shining and snow covers the panels. They do
not provide power to the inverter.

```bash
~/solar_checker $ apsystems_max_power_set.py --ip apsystems --max_power 799
ERROR:apsystems_max_power_set.py:Cannot connect to inverter.
~/solar_checker $
```

Some time later it becomes brighter and the panels deliver at least some
power.

```bash
~/solar_checker/scripts $ apsystems_max_power_set.py --ip apsystems
INFO:apsystems_max_power_set.py:Current Max Power Limit: 300W
~/solar_checker/scripts $ apsystems_max_power_set.py --ip apsystems --max_power 800
INFO:apsystems_max_power_set.py:The power limit for inverters in Germay is 600W.
INFO:apsystems_max_power_set.py:Be advised to consult your lawyer!
INFO:apsystems_max_power_set.py:Current Max Power Limit: 300W
INFO:apsystems_max_power_set.py:Commanded Power: 800W
INFO:apsystems_max_power_set.py:New_Power: 800W
INFO:apsystems_max_power_set.py:Commanded Power Status: ON
INFO:apsystems_max_power_set.py:New Power Status: ON
~/solar_checker/scripts $ apsystems_max_power_set.py --ip apsystems --max_power 600
INFO:apsystems_max_power_set.py:Current Max Power Limit: 800W
INFO:apsystems_max_power_set.py:Commanded Power: 600W
INFO:apsystems_max_power_set.py:New_Power: 600W
INFO:apsystems_max_power_set.py:Commanded Power Status: ON
INFO:apsystems_max_power_set.py:New Power Status: ON
~/solar_checker/scripts $
```

Have a look at the current power and total energy consumed in your house!

```bash
~/solar_checker/scripts $ tasmota_latest_get.py --ip tasmota| \
                             awk -F',' '{printf("Power:%.0fW\nEnergy:%.0fkWh\n", $2,$3)}'
Power:4W
Energy:4227kWh
~/solar_checker/scripts $ apsystems_latest_get.py --ip apsystems
24,0.032,0.698,24,0.029,0.658
~/solar_checker/scripts $ apsystems_latest_get.py --ip apsystems| \
                          awk -F',' '{printf("Channel1: %.0fW %.3fkWh %.3fkWh\n", $1, $2,$3)}'
Channel1: 26W 0.034kWh 0.700kWh
~/solar_checker/scripts $ apsystems_latest_get.py --ip apsystems| \
                         awk -F',' '{printf("Channel 1: %.0fW %.3fkWh %.3fkWh\nChannel 2: %.0fW %.3fkWh %.3fkWh\n", $1,$2,$3,$4,$5,$6)}'
Channel 1: 25W 0.035kWh 0.701kWh
Channel 2: 24W 0.032kWh 0.661kWh
~/solar_checker/scripts $
```
---

## Disclaimer

During the installation of the Anker Solix 1600 solarbank the firmware
of the APsystems EZ1M was overidden in such a way that its 'Local Mode'
is not available anymore. Testing of the inverter is not possible
anymore and development is skipped until Anker, APsystems, and/or my
dealer's support find a solution rather delegating responsibilty to
the others.

---
