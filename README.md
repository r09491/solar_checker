# Solar Checker -  Python Library

## Overview

The Solar Checker Python library provides APIs for the  APsystems EZ1 Microinverters and smartmeter sensors with Tasmoto. Based on these two APIs there are scripts to record their latest power data which in turn can be used for plots to visualise them. It facilitates the process to monitor a solar power station and to assess if it will pay off at a point of time,  

---

## Features

- **Get detailed device information**
- **Retrieve alarm status information**
- **Fetch output data** (power output, energy readings)
- **Set and get maximum power limits** (30 W up to 800 W)
- **Manage device power status** (sleep_mode/on/off)
- **Calculate combined power output and total energy generated**


---

## Setup your Inverter

The local API access needs to be activated once in the settings of the APsystems Easy Power App. 
<ul>
<li>Step 1: Connect to the inverter using the "Direct Connection" method.</li>
<li>Step 2: Establish a connection with your inverter.</li>
<li>Step 3: Select the Settings menu.</li>
<li>Step 4: Switch to the "Local Mode" section.</li>
<li>Step 5: Activate local mode and select "Continuous"</li>
<li>Step 6: By some magic the inverter will be added to your Homenet. The inverter runs an HTTP server on port 8050</li>
</ul>

---

## Setup Tasmota for your Smartmeter

There are lot of instructions on how to setup Tasmota for a smartmeter on the internet.

---

## Installation

- To use the apsystems and tosmota library, you need to have Python >=3.11 installed on your system. I installed python 3.12 on a raspberry. The libraries and the recording work fine. Unfortunately to install numpy  gcc 8.4  is required which is not available by default. As a result the plot script has to be run on another machine. Since I store my recordings on a Samba server this is no problem.
- See the following guide to install the latest Python release: <https://www.python.org/downloads> <br><br>

<ul>
<li>Step 1: git clone the repository</li>
<li>Step 2: cd to the directory solar_checker</li>
<li>Step 3: install with pip</li>
</ul>

```bash
cd solar_checker
pip install .
```

For the recording see two cron scripts and run them in cron.

---

