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

WATTS_SOC = ["soc", "socmin", "socmax", "soctime"] # 0 - 100, minutes
WATTS_SUM = ['sumin', 'sumout']
WATTS_USB = ['usb1', 'usb2', 'qc1', 'qc2', 'pd1', 'pd2']
WATTS_AC = ['acin', 'acout', 'accharge']
WATTS_XT60 = ['xt60']
WATTS_12V = ['12V']
WATTS = WATTS_SOC + WATTS_SUM + WATTS_USB + WATTS_AC + WATTS_XT60 + WATTS_12V 


MIN_GRID_WATTS = -400
MAX_GRID_WATTS = 400
MIN_CHARGE_WATTS = 100
MAX_CHARGE_WATTS = 600

CHARGE_STEP = 10

class Delta_Max(Device):
    
    def __init__(self, timeout: int = 10):
        super().__init__()
        self.url, self.key, self.secret, self.sn = get_dot_ecoflow_api()


    async def get_ac_out_enabled(self) -> int:    
        quotas = ["inv.cfgAcEnabled"]
        return await self.get_quotas(quotas)

    async def set_ac_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled": enabled, "id":66}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})


    async def get_usb_out_enabled(self) -> int:
        quotas = ["pd.dcOutState"]
        return await self.get_quotas(quotas)

    async def set_usb_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled":enabled, "id":34}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})

        
    async def get_12V_out_enabled(self) -> int:
        quotas = ["mppt.carState"]
        return await self.get_quotas(quotas)

    async def set_12V_out_enabled(self, enabled: int) -> None:
        params  = {"cmdSet":32, "enabled": enabled, "id":81}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})
        

    async def get_beep_muted(self) -> int:
        quotas = ["pd.beepState"]
        return await self.get_quotas(quotas)

    async def set_beep_muted(self, muted: int) -> None:
        params  = {"cmdSet":32, "id":38, "enabled":muted}
        payload = await self.put({"sn": self.sn, "operateType": "TCP", "params": params})
        ##print('Response:')
        ##print(json.dumps(payload,indent=4))
        

    async def get_ac_charge_watts(self) -> int:
        quotas = ["inv.cfgSlowChgWatts"]
        return await self.get_quotas(quotas)

    async def set_ac_charge_watts(self, watts: int) -> None:
        params  = {"cmdSet":32, "slowChgPower":watts, "id":69}
        payload = await self.put({"moduleType":0, "sn": self.sn, "operateType": "TCP", "params": params})


    async def get_sum_watts(self) -> list:
        quotas = ["pd.wattsInSum", "pd.wattsOutSum"]
        return await self.get_quotas(quotas)

    
    async def get_12V_watts(self) -> list:
        quotas = ["mppt.carOutWatts"]
        watts = await self.get_quotas(quotas)
        watts[0] = int(watts[0]/10)
        return watts
    
    async def get_usb_watts(self) -> list:
        quotas = ["pd.usb1Watts", "pd.usb2Watts"]
        quotas += ["pd.qcUsb1Watts", "pd.qcUsb2Watts"]
        quotas += ["pd.typec1Watts", "pd.typec2Watts"]
        return await self.get_quotas(quotas)

    
    async def get_ac_watts(self) -> list:
        quotas = ["inv.inputWatts", "inv.outputWatts"]
        return await self.get_quotas(quotas)

    
    async def get_watts(self) -> dict:
        quotas = ["pd.soc"]
        quotas += ["ems.minDsgSoc", "ems.maxChargeSoc"]
        quotas += ["pd.remainTime"]
        quotas += ["pd.wattsInSum", "pd.wattsOutSum"]
        quotas += ["pd.usb1Watts", "pd.usb2Watts"]
        quotas += ["pd.qcUsb1Watts", "pd.qcUsb2Watts"]
        quotas += ["pd.typec1Watts", "pd.typec2Watts"]
        quotas += ["inv.inputWatts", "inv.outputWatts", "inv.cfgSlowChgWatts"]
        quotas += ["mppt.inWatts"]
        quotas += ["mppt.carOutWatts"]
        watts = await self.get_quotas(quotas)
        watts[-2] = int(watts[-2]/10)
        watts[-1] = int(watts[-1]/10)
        return dict(zip(WATTS, watts)) # ordered per quotas

    
    async def get_ac_in_out_charge_watts(self) -> list:
        quotas = ["inv.inputWatts", "inv.outputWatts", "inv.cfgSlowChgWatts"]
        return await self.get_quotas(quotas)

    async def set_ac_charge_watts_balance(self,
            smp: int = None,
            minp: int = MIN_CHARGE_WATTS,
            maxp :int = MAX_CHARGE_WATTS) -> Optional[int]:
        
        acpi, acpo, acpc0 = await self.get_ac_in_out_charge_watts()

        info = 'DM balancing inputs'
        info += f' SMP:{smp},'
        info += f' ACPI:{acpi},'
        info += f' ACPO:{acpo},'
        info += f' ACPC:{acpc0}'
        logger.info(info)

        if ((smp is None) or
            (acpi is None) or
            (acpo is None) or
            (acpc0 is None)):
            logger.warn(f'Missing inputs. Abort!')
            return None
            
        if (acpi <= acpo):
            logger.info(f'No AC charging. Abort!')
            return None

        if (smp == 0): #Ok, since int
            logger.info(f'No charge request. Abort!')
            return None
        
        acpc_delta = int(smp)
        if (abs(acpc_delta) < CHARGE_STEP):
            logger.info(f'Charge rate delta "{acpc_delta}" too small. Ignore!')
            return None

        acpc1 = CHARGE_STEP*int(min(max((acpc0-acpc_delta),minp),maxp)/CHARGE_STEP)
        if (abs(acpc1 - acpc0)  < CHARGE_STEP):
            logger.info(f'New charge rate "{acpc1}" too close. Ignore!')
            return None
            
        logger.info(f'Trying to update the charge rate to "{acpc1}" by "{acpc_delta}"')        
        await self.set_ac_charge_watts(acpc1)
        
        for i in range(3):
            await asyncio.sleep(5)
            acpc1 = await self.get_ac_charge_watts()
            if acpc1 != acpc0 or acpc1==minp:
                logger.info(f'Charge rate update confirmed "{acpc1}"')
                return acpc1

        logger.warn(f'DM did not confirm charge rate update"')            
        return None
