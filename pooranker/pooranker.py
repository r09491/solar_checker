__doc__=""" This is a poor anker libray to get the latest power data
from a Anker Solix solarbank.

It uses the anker-solix-api.  See the anker-solix-api repository on
github.com.
"""
__version__ = "0.0.1"
__author__ = "r09491@gmail.com"

import sys
import os
import json

from datetime import datetime

import asyncio
from aiohttp import ClientSession

from anker_solix_api.api import AnkerSolixApi
from anker_solix_api.types import SolarbankTimeslot

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

    
    def __init__(self):
        self._credentials = self._get_credentials()


    async def get_power_data(self) -> Optional[Power_Data]:
        async with ClientSession() as cs:
            if self._credentials is None:
                logger.error(f'credentials are not available.')
                return None
            
            sapi = AnkerSolixApi(*self._credentials, cs, None)
            await sapi.update_sites()
            device_sn = list(sapi.devices)[0]
            
            logger.info(f'updated data for serial number "{device_sn}"')

            """ Currently data from only one solarbank is handled """

            device_data = sapi.devices[device_sn]
            status = device_data['status_desc']        
            if status != 'online':
                logger.error(f'wrong solarbank status "{status}"')
                return None            
            
            input_power = float(device_data['input_power'])
            output_power = float(device_data['output_power'])
            charging_power = float(device_data['charging_power'])
            battery_power = output_power - input_power
            battery_soc = float(device_data['battery_soc'])/100.0

            logger.info(f'Charging power >>>>> "{charging_power}"')
            logger.info(f'Battery power >>>>> "{battery_power}"')
            
            return Power_Data(input_power, output_power,
                              battery_power, battery_soc)


    async def set_home_load(self,
                            home_load: int,
                            start_time: str = "00:00",
                            stop_time : str = "23:59") -> bool:
        
        async with ClientSession() as cs:
            if self._credentials is None:
                logger.error(f'credentials are not available.')
                return False

            sapi = AnkerSolixApi(*self._credentials, cs, None)
            await sapi.update_sites()
            device_sn = list(sapi.devices)[0]
            logger.info(f'updated data for serial number "{device_sn}"')

            device_data = sapi.devices[device_sn]
            
            is_admin = device_data['is_admin']
            if not is_admin:
                logger.error(f'setting allowed by admin only')
                return False

            status = device_data['status_desc']        
            if status != 'online':
                logger.info(f'wrong status of solarbank "{status}"')
                return False

            site_id = device_data['site_id']    
            logger.info(f'id of site is "{site_id}"')

            await sapi.set_home_load(
                siteId=site_id,
                deviceSn=device_sn,
                preset=None,
                dev_preset=None,
                all_day=None,
                export=None,
                charge_prio=None,
                insert_slot=SolarbankTimeslot(
                    start_time=datetime.strptime(start_time, "%H:%M"),
                    end_time=datetime.strptime(stop_time, "%H:%M"),
                    appliance_load=home_load,
                    device_load=None,
                    allow_export=None,
                    charge_priority_limit=None,
                ),
            )

            logger.info(f'home load is set to "{home_load}".')
            return True


    async def clear_home_load(self) -> bool:
        
        async with ClientSession() as cs:
            if self._credentials is None:
                logger.error(f'credentials are not available.')
                return False

            sapi = AnkerSolixApi(*self._credentials, cs, None)
            await sapi.update_sites()
            device_sn = list(sapi.devices)[0]

            logger.info(f'updated data for serial number "{device_sn}"')

            device_data = sapi.devices[device_sn]

            is_admin = device_data['is_admin']
            if not is_admin:
                logger.error(f'setting allowed by admin only')
                return False
            
            status = device_data['status_desc']        
            if status != 'online':
                logger.info(f'wrong status of solarbank : "{status}"')
                return False

            site_id = device_data['site_id']    
            logger.info(f'Id of site is "{site_id}"')
            
            await sapi.set_home_load(
                siteId=site_id,
                deviceSn=device_sn,
                preset=None,
                dev_preset=None,
                all_day=None,
                export=None,
                charge_prio=None,
                insert_slot=None,
            )

            logger.info(f'home load is reset.')
            return True
