__doc__=""" A python library for the APsystems API in local mode

Heavily influenced by the the github APsystems EZ1 repository
"""
__version__ = "0.0.2"
__author__ = "r09491@gmail.com"

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest

from enum import IntEnum
from dataclasses import dataclass

import sys
if sys.version_info >= (3, 9): 
    from typing import Optional, Any
    ReturnRequest = Optional[dict[str, Any]]
else:
    from typing import Optional, Any, Dict
    ReturnRequest = Optional[Dict[str, Any]]
    
class Status(IntEnum):
    normal = 0
    alarm = 1


@dataclass
class ReturnDeviceInfo:
    deviceId: str
    devVer: str
    ssId: str
    ipAddr: str
    minPower: int
    maxPower: int


@dataclass
class ReturnAlarmInfo:
    og: Status
    isce1: Status
    isce2: Status
    oe: Status


@dataclass
class ReturnOutputData:
    p1: float
    e1: float
    te1: float
    p2: float
    e2: float
    te2: float


class Inverter:

    def __init__(self, ip_address: str, port: int = 8050, timeout: int = 10):
        self.base_url = f"http://{ip_address}:{port}"
        self.timeout = timeout

        
    async def _request(self, endpoint: str) -> ReturnRequest:
        url = f"{self.base_url}/{endpoint}"
        try:
            async with ClientSession() as ses, ses.get(url, timeout=self.timeout) as resp:
                if not resp.ok:
                    raise HttpBadRequest(f"HTTP Error: {resp.status}")
                return await resp.json() # type: ignore[no-any-return]
        except:
            return None

        
    async def get_device_info(self) -> Optional[ReturnDeviceInfo]:
        try:
            response = await self._request("getDeviceInfo")
        except:
            respone = None
        data = response.get("data") if response else None
        return (
            ReturnDeviceInfo(
                deviceId=data["deviceId"],
                devVer=data["devVer"],
                ssId=data["ssId"],
                ipAddr=data["ipAddr"],
                minPower=int(data["minPower"]),
                maxPower=int(data["maxPower"]),
            )
            if data else None
        )

    
    async def get_alarm_info(self) -> Optional[ReturnAlarmInfo]:
        try:
            response = await self._request("getAlarm")
        except:
            response = None
        data = response.get("data") if response else None
        return (
            ReturnAlarmInfo(
                og=Status(int(data["og"])),
                isce1=Status(int(data["isce1"])),
                isce2=Status(int(data["isce2"])),
                oe=Status(int(data["oe"])),
            )
            if data else None
        )

    
    async def get_output_data(self) -> Optional[ReturnOutputData]:
        try:
            response = await self._request("getOutputData")
        except:
            respone = None
        data = response.get("data") if response else None
        return ReturnOutputData(**data) if data else None

    
    async def get_total_output(self) -> Optional[float]:
        data = await self.get_output_data()
        return float(data.p1 + data.p2) if data else None

    
    async def get_total_energy_today(self) -> Optional[float]:
        data = await self.get_output_data()
        return float(data.e1 + data.e2) if data else None

    
    async def get_total_energy_lifetime(self) -> Optional[float]:
        data = await self.get_output_data()
        return float(data.te1 + data.te2) if data else None

    
    async def get_max_power(self) -> Optional[int]:
        try:
            response = await self._request("getMaxPower")
        except:
            respone = None
        data = response.get("data") if response else None
        max_power = data.get("maxPower") if data  else None
        return int(max_power) if max_power else None

    
    async def set_max_power(self, power_limit: int) -> Optional[int]:
        if not 30 <= power_limit <= 800:
            raise ValueError(
                f"Invalid set_max_Power value: '{power_limit}'"
            )
        try:
            request = await self._request(f"setMaxPower?p={power_limit}")
        except:
            reuest = None
        data = request.get("data") if request else None
        max_power = data.get("maxPower") if data else None
        return int(max_power) if max_power else None

    
    async def get_device_power_status(self) -> Optional[Status]:
        try:
            response = await self._request("getOnOff")
        except:
            response = None
        data = response.get("data") if response else None
        onoff = data.get("status") if data else None
        return Status(int(onoff)) if onoff else None

    
    async def set_device_power_status(self, power_status: Status) -> Optional[Status]:
        status_map = {"0": "0", "ON": "0", "1": "1", "SLEEP": "1", "OFF": "1"}
        status_value = status_map.get(str(power_status.value))
        if status_value is None:
            raise ValueError(
                f"Invalid power status: '{str(power_status.value)}'"
            )
        try:
            request = await self._request(f"setOnOff?status={status_value}")
        except:
            request = None
        data = request.get("data") if request else None
        onoff = data.get("status") if data else None
        return Status(int(onoff)) if onoff else None

    
    async def is_power_on(self) -> bool:
        try:
            power_status = await self.get_device_power_status()
        except:
            power_status = None
        return  bool(power_status == Status(0)) if power_status is not None else False
