__doc__=""" This is a poor anker libray to get the latest power data
from a Anker Solix solarbank.

It uses the anker-solix-api.  See the anker-solix-api repository on
github.com.
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import sys
import os
import json

import asyncio
from aiohttp import ClientSession

from anker_solix_api.api import AnkerSolixApi

from typing import Optional, Any
from dataclasses import dataclass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__file__)


@dataclass
class Power_Data:
    input_power: float   # Watt
    output_power: float  # Watt
    battery_power: float # Watt negativ for charging, positiv for discharging
    battery_soc: float    # %

        
class Solarbank():

    def _get_credentials(self) -> Optional[list]:
        cjson = None
        home = os.path.expanduser('~')
        cnames = [".pooranker", os.path.join(home, ".pooranker" )]
        for cn in cnames:
            try:
                with open(cn, "r") as cf:
                    cjson = json.load(cf)
                    break
            except:
                logger.warn(f'Reading credentials from {cn} failed.')
                continue
        logger.info(f'Reading credentials ok')
        return list(cjson.values()) if cjson else None 

    
    def __init__(self, serial_number: str):
        self._credentials = self._get_credentials()
        self._serial_number = serial_number

        
    async def get_power_data(self) -> Optional[Power_Data]:
        async with ClientSession() as cs:
            sapi = AnkerSolixApi(*self._credentials, cs, None)
            await sapi.update_sites()
            device_sn = list(sapi.devices)[0]
            logger.info(f'Updated data for serial number "{device_sn}"')

            """ Currently data from one solarbank only are
            handeled. If there are more the first is used """

            device_data = sapi.devices[device_sn]
            status = device_data['status_description']
            logger.info(f'Current solarbank status is "{status}"')
            
            input_power = float(device_data['input_power'])
            output_power = float(device_data['output_power'])
            battery_power = output_power - input_power
            battery_soc = float(device_data['battery_soc'])/100.0

            return Power_Data(input_power, output_power,
                              battery_power, battery_soc)

        return None

