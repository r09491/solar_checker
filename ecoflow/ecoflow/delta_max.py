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

from .helpers import (
    get_dot_ecoflow_api
)

from .device import Device
    
class Delta_Max(Device):
    
    def __init__(self, timeout: int = 10):
        super().__init__()
        self.url, self.key, self.secret, self.sn = get_dot_ecoflow_api()


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

    async def set_ac_charge_watts_balance(self,
                                          smp: int = None,
                                          minp: int = 100,
                                          maxp :int = 800) -> Optional[int]:
        acpi, acpo, acpc0, soc = await self.get_ac_in_out_charge_watts_soc()

        info = 'DM balancing inputs'
        info += f' SMP:{smp},'
        info += f' ACPI:{acpi},'
        info += f' ACPO:{acpo},'
        info += f' ACPC:{acpc0},'
        info += f' SOC:{soc}'
        logger.info(info)

        if smp is None or (smp == 0) or (acpi == 0):
            logger.warn(f'DM keeping charge rate. Abort!')
            return None

        #acpc_delta = int(smp/2)
        acpc_delta = int(smp)
        if abs(acpc_delta) < 10:
            logger.warn(f'Charge rate delta "{acpc_delta}" too low. Ignore!')
            return None

        acpc_new = min(max(acpc0-acpc_delta,minp),maxp)
        if abs(acpc_new - acpc0)  < 10:
            logger.warn(f'Charge rate new "{acpc_new}" too close. Ignore!')
            return None
        
        logger.info(f'Trying to update the charge rate to "{acpc_new}" by "{acpc_delta}"')        
        await self.set_ac_charge_watts(acpc_new)
        logger.info(f'Charge rate update commanded!')
        
        for i in range(3):
            await asyncio.sleep(2)
            acpc1 = await self.get_ac_charge_watts()
            if acpc1 != acpc0 or acpc1==minp:
                logger.info(f'DM charge rate update is confirmed "{acpc1}"')
                return acpc1

        logger.warn(f'DM did not confirm charge rate update"')            
        return None
