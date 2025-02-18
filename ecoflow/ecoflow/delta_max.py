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

WATTS_SOC = ["soc", "minsoc", "maxsoc"] # 0 - 100

WATTS_RTIME = ["rtime"] # Minutes

WATTS_SUM = ['sumin', 'sumout']

WATTS_12V = ['12V']

WATTS_USB = ['usb1', 'usb2', 'qc1', 'qc2', 'pd1', 'pd2']

WATTS_AC = ['acin', 'acout']

WATTS_XT60 = ['xt60']

WATTS = WATTS_SOC + WATTS_RTIME + WATTS_SUM + WATTS_12V + WATTS_USB + WATTS_AC


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
        quotas += ["ems.minDsgSoc", "ems.maxChargeSoc", "ems.chRemainTime"]
        quotas += ["pd.wattsInSum", "pd.wattsOutSum"]
        quotas += ["mppt.carOutWatts"]
        quotas += ["pd.usb1Watts", "pd.usb2Watts"]
        quotas += ["pd.qcUsb1Watts", "pd.qcUsb2Watts"]
        quotas += ["pd.typec1Watts", "pd.typec2Watts"]
        quotas += ["inv.inputWatts", "inv.outputWatts"]
        watts = await self.get_quotas(quotas)
        watts[3] = int(watts[6]/10)
        xt60_watts = [watts[4] - watts[-2]] # To be checked: values if no solar
        return dict(zip(WATTS+WATTS_XT60, watts + xt60_watts)) # ordered per quotas

    
    async def get_ac_in_out_charge_watts(self) -> list:
        quotas = ["inv.inputWatts", "inv.outputWatts", "inv.cfgSlowChgWatts"]
        return await self.get_quotas(quotas)

    async def set_ac_charge_watts_balance(self,
                                          smp: int = None,
                                          minp: int = 100,
                                          maxp :int = 800) -> Optional[int]:
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
            
        if (acpi == 0):
            logger.info(f'No AC charging. Abort!')
            return None

        if (smp == 0):
            logger.info(f'No change request. Abort!')
            return None
        
        acpc_delta = int(smp)
        if (abs(acpc_delta) < 10):
            logger.info(f'New charge rate delta "{acpc_delta}" too small. Ignore!')
            return None

        acpc1 = min(max((acpc0-acpc_delta),minp),maxp)
        if (abs(acpc1 - acpc0)  < 10):
            logger.info(f'New charge rate "{acpc1}" too close. Ignore!')
            return None
            
        logger.info(f'Trying to update the charge rate to "{acpc1}" by "{acpc_delta}"')        
        await self.set_ac_charge_watts(acpc1)
        logger.info(f'Charge rate update commanded!')
        
        for i in range(3):
            await asyncio.sleep(2)
            acpc1 = await self.get_ac_charge_watts()
            if acpc1 != acpc0 or acpc1==minp:
                logger.info(f'New charge rate update confirmed "{acpc1}"')
                return acpc1

        logger.warn(f'DM did not confirm charge rate update"')            
        return None
