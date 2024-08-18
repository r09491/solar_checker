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

import asyncio
from aiohttp import ClientSession

from anker_solix_api.api import AnkerSolixApi
from anker_solix_api.types import SolixParmType, SolarbankStatus

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
    battery_soc: float   # %

        
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
                logger.warn(f'reading credentials from {cn} failed.')
                continue
        logger.info(f'reading credentials ok')
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
            battery_power = -float(device_data['charging_power'])
            battery_soc = float(device_data['battery_soc'])/100.0
            
            return Power_Data(input_power, output_power,
                              battery_power, battery_soc)

    """ Set the output power of the Anker Solarbank. It takes upto
    three minutes to settle after the command start. During the first
    minute the output power drops down. Then approaches the commanded
    value. There are conditions the bank is not able to meet the
    request, eg when the battery is full and/or low solar radiation
    even if commanded. Be aware of the latencies in the Anker cloud!
    """
    async def set_home_load(self,
                            home_load: int, # Watt
                            start_time: str = "00:00",
                            end_time : str = "23:59") -> bool:

        """ Fill the schedule with input """
        schedule_sb1 = {
            "ranges": [
                {
                    "id":0,
                    "start_time": start_time,
                    "end_time": end_time,
                    "turn_on": True,
                    "appliance_loads": [
                        {
                            "id":0,
                            "name":"PoorAnker",
                            "power": home_load,
                            "number":1
                        }
                    ],
                }
            ],
        }
        
        async with ClientSession() as cs:
            if self._credentials is None:
                logger.error(f'credentials are not available.')
                return False

            sapi = AnkerSolixApi(*self._credentials, cs, None)

            await sapi.update_sites()
            device_sn = list(sapi.devices)[0]
            logger.info(f'updated data for serial number "{device_sn}"')

            device_data = sapi.devices[device_sn]

            device_pn = device_data['device_pn']
            if device_pn != 'A17C0':
                logger.error(f'setting allowed for solarbank 1 only')
                return False

            status = device_data['status_desc']        
            if status != 'online':
                logger.info(f'wrong status of solarbank "{status}"')
                return False

            is_admin = device_data['is_admin']
            if not is_admin:
                logger.error(f'setting allowed by admin only')
                return False

            site_id = device_data['site_id']    
            logger.info(f'id of site is "{site_id}"')

            charging_status = SolarbankStatus(device_data['charging_status'])
            logger.info(f'charging status is "{charging_status}"')
            if not ((charging_status == SolarbankStatus.discharge) or
                    (charging_status == SolarbankStatus.charge) or
                    (charging_status == SolarbankStatus.bypass) or
                    (charging_status == SolarbankStatus.bypass_charge)):
                logger.warning(f'wrong charging status "{charging_status}"')
                return False

            set_output_power = int(device_data['set_output_power'])
            if home_load-10 < set_output_power < home_load+10:
                logger.info(f'home load is kept to "{set_output_power}"')
                return True
            
            is_done= await sapi.set_device_parm(
                siteId = site_id,                                   
                deviceSn = device_sn,
                paramData = schedule_sb1, 
                paramType = SolixParmType.SOLARBANK_SCHEDULE.value)

            if is_done:
                logger.info(f'home load is set to "{home_load}"')
            else:
                logger.error(f'home load setting failed"')
            return is_done
