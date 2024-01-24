__doc__=""" A python library for the Tasmota Smartmeter API
"""
__version__ = "0.0.2"
__author__ = "r09491@gmail.com"


from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest

from dataclasses import dataclass

import sys
if sys.version_info >= (3, 9): 
    from typing import Optional, Any
    ReturnRequest = Optional[dict[str, Any]]
else:
    from typing import Optional, Any, Dict
    ReturnRequest = Optional[Dict[str, Any]]


@dataclass
class Return_Status_SNS:
    time: str
    energy: float
    power: float

    
class Smartmeter:

    def __init__(self, ip_address: str, port: int = 80, timeout: int = 10):
        self.base_url = f"http://{ip_address}:{port}"
        self.timeout = timeout

        
    async def _request(self, command: str, para: str) -> ReturnRequest:
        url = f"{self.base_url}/cm?cmnd={command}+{para}"
        try:
            async with ClientSession() as ses, ses.get(url, timeout=self.timeout) as resp:
                if not resp.ok:
                    raise HttpBadRequest(f"HTTP Error: {resp.status}")
                return await resp.json() # type: ignore[no-any-return]
        except:
            return None


    async def get_status_sns(self) -> Optional[Return_Status_SNS]:
        try:
            response = await self._request(command = "status", para = "8")
        except:
            respone = None
        status_sns =  response["StatusSNS"] if response else None
        values = list(status_sns.values()) if status_sns else None
        return Return_Status_SNS(values[0], **values[-1]) if values else None

    
    async def get_power(self) -> Optional[float]:
        try:
            status_sns = await self.get_status_sns()
        except:
            status_sns = None
        return status_sns.power if status_sns else None
    
    
    async def get_energy_total_lifetime(self) -> Optional[float]:
        try:
            status_sns = await self.get_status_sns()
        except:
            status_sns = None
        return status_sns.energy if status_sns else None


    async def has_power(self) -> Optional[bool]:
        try:
            response = await self._request(command = "status", para = "0")
        except:
            response = None
        status = response.get("Status") if response else None
        power = status.get("Power") if status else None
        return bool(power) if power else None

    
    async def is_power_on(self) -> bool:
        try:
            response = await self._request(command = "status", para = "0")
        except:
            response = None
        status = response.get("Status") if response else None 
        power_on = status.get("Power") and status.get("PowerOnState") if status else None
        return bool(power_on) if power_on else False
