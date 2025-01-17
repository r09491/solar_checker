__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import sys
import os
import json
import asyncio        

from typing import Optional

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest

from .helpers import (
    get_headers,
    get_dot_ecoflow_api
)


class Device():
    
    def __init__(self, timeout: int = 10):
        self.url, self.key, self.secret, _ = get_dot_ecoflow_api()
        self.timeout = timeout

    
    async def _get(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.get(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

    async def _post(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.post(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

    async def _put(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.put(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

            
    def _get_headers(self, params: dict):
        return get_headers(self.key, self.secret, params)
            
    async def get(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._get(headers=headers, json=params)

    async def post(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._post(headers=headers, json=params)

    async def put(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._put(headers=headers, json=params)

    
class Delta_Max(Device):
    
    def __init__(self, timeout: int = 10):
        super().__init__()
        # The 4th line has the serial number of the Delta Max
        _, _, _, self.sn = get_dot_ecoflow_api() 


    async def get_ac_out_enabled(self) -> int:    
        quotas = ["inv.cfgAcEnabled"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        return payload.get("data").get("inv.cfgAcEnabled")

    async def set_ac_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled": enabled, "id":66}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})


    async def get_usb_out_enabled(self) -> int:
        quotas = ["pd.dcOutState"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        data = payload.get("data")
        return data.get("pd.dcOutState")

    async def set_usb_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled":enabled, "id":34}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})

        
    async def get_12V_out_enabled(self) -> int:
        quotas = ["mppt.carState"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        return payload.get("data").get("mppt.carState")

    async def set_12V_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled": enabled, "id":81}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})
        

    async def get_beep_muted(self) -> int:
        quotas = ["pd.beepState"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        return payload.get("data").get("pd.beepState")

    async def set_beep_muted(self, muted: int) -> None:
        params  = {"cmdSet":32, "id":38, "enabled":muted}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})
        ##print('Response:')
        ##print(json.dumps(payload,indent=4))
        

    async def get_ac_charge_watts(self) -> int:
        quotas = ["inv.cfgSlowChgWatts"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        return int(payload.get("data").get("inv.cfgSlowChgWatts"))

    async def set_ac_charge_watts(self, watts: int) -> None:
        params  = {"cmdSet":32, "slowChgPower":watts, "id":69}
        payload = await self.put({"moduleType":0, "sn": self.sn, "operateType": "TCP", "params": params})


    async def get_ac_in_out_charge_watts_soc(self) -> int:
        quotas = ["inv.inputWatts", "inv.outputWatts", "inv.cfgSlowChgWatts", "pd.soc"]
        params = {"quotas": quotas}
        payload = await self.post({"sn": self.sn, "params": params})
        data = payload.get("data")
        return [data.get(q) for q in quotas] # ordered per quotas

    async def set_ac_charge_watts_balance(self, smp: int,
                                          minp: int = 100,
                                          maxp :int = 2000) -> Optional[int]:
        acpc0 = await self.get_ac_charge_watts()
        if smp == 0:
            return acpc0
        
        await self.set_ac_charge_watts(min(max(acpc0-smp,minp),maxp))
        
        for i in range(3):
            await asyncio.sleep(2)
            acpc1 = await self.get_ac_charge_watts()
            if acpc1 != acpc0 or acpc1==minp:
                return acpc1
            
        return None
