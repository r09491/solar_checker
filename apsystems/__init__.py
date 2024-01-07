from dataclasses import dataclass
from enum import IntEnum

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest


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


class EZ1M:

    def __init__(self, ip_address: str, port: int = 8050, timeout: int = 10):
        self.base_url = f"http://{ip_address}:{port}"
        self.timeout = timeout

        
    async def _request(self, endpoint: str) -> dict | None:
        url = f"{self.base_url}/{endpoint}"
        async with ClientSession() as ses, ses.get(url, timeout=self.timeout) as resp:
            if not resp.ok:
                raise HttpBadRequest(f"HTTP Error: {resp.status}")
            return await resp.json()

        
    async def get_device_info(self) -> ReturnDeviceInfo | None:
        response = await self._request("getDeviceInfo")
        data = response["data"] if response and response.get("data") else None
        return (
            ReturnDeviceInfo(
                deviceId=data["deviceId"],
                devVer=data["devVer"],
                ssId=data["ssId"],
                ipAddr=data["ipAddr"],
                minPower=int(data["minPower"]),
                maxPower=int(data["maxPower"]),
            )
            if data
            else None
        )

    
    async def get_alarm_info(self) -> ReturnAlarmInfo | None:
        response = await self._request("getAlarm")
        data = response["data"] if response and response.get("data") else None
        return (
            ReturnAlarmInfo(
                og=Status(int(data["og"])),
                isce1=Status(int(data["isce1"])),
                isce2=Status(int(data["isce2"])),
                oe=Status(int(data["oe"])),
            )
            if data
            else None
        )

    
    async def get_output_data(self) -> ReturnOutputData | None:
        response = await self._request("getOutputData")
        data = response["data"] if response and response.get("data") else None
        return ReturnOutputData(**data) if data else None

    
    async def get_total_output(self) -> float | None:
        data = await self.get_output_data()
        return float(data.p1 + data.p2) if data else None

    
    async def get_total_energy_today(self) -> float | None:
        data = await self.get_output_data()
        return float(data.e1 + data.e2) if data else None

    
    async def get_total_energy_lifetime(self) -> float | None:
        data = await self.get_output_data()
        return float(data.te1 + data.te2) if data else None

    
    async def get_max_power(self) -> int | None:
        response = await self._request("getMaxPower")
        data = response["data"] if response and response.get("data") else None
        max_power = data["maxPower"] if data and data["maxPower"] != "" else None
        return int(max_power) if max_power else None

    
    async def set_max_power(self, power_limit: int) -> int | None:
        if not 30 <= power_limit <= 800:
            raise ValueError(
                f"Invalid setMaxPower value: expected int between '30' and '800', got '{power_limit}'"
            )
        request = await self._request(f"setMaxPower?p={power_limit}")
        data = request["data"] if request and request.get("data") else None
        max_power = data["maxPower"] if data and data["maxPower"] != "" else None
        return int(max_power) if max_power else None

    
    async def get_device_power_status(self) -> Status | None:
        response = await self._request("getOnOff")
        data = response["data"] if response and response.get("data") else None
        onoff = data["status"] if data and data["status"] != "" else None
        return Status(int(onoff)) if onoff else None

    
    async def set_device_power_status(self, power_status: Status | None) -> Status | None:
        status_map = {"0": "0", "ON": "0", "1": "1", "SLEEP": "1", "OFF": "1"}
        status_value = status_map.get(str(power_status))
        if status_value is None:
            raise ValueError(
                f"Invalid power status: expected '0', 'ON' or '1','SLEEP' or 'OFF', got '{str(power_status)}"
                + "'\n Set '0' or 'ON' to start the inverter | Set '1' or 'SLEEP' or 'OFF' to stop the inverter."
            )
        request = await self._request(f"setOnOff?status={status_value}")
        data = request["data"] if request and request.get("data") else None
        onoff = data["status"] if data and data["status"] != "" else None
        return Status(int(onoff)) if onoff else None

    
    async def is_power_on(self) -> bool:
        power_status = await self.get_device_power_status()
        return  power_status == Status(0) if power_status else False
