from dataclasses import dataclass

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest


@dataclass
class Return_Status_SNS:
    time: str
    energy: float
    power: float

    
class Smartmeter:

    def __init__(self, ip_address: str, port: int = 80, timeout: int = 10):
        self.base_url = f"http://{ip_address}:{port}"
        self.timeout = timeout

        
    async def _request(self, command: str, para: str |int) -> dict | None:
        url = f"{self.base_url}/cm?cmnd={command}+{para}"
        async with ClientSession() as ses, ses.get(url, timeout=self.timeout) as resp:
            if not resp.ok:
                raise HttpBadRequest(f"HTTP Error: {resp.status}")
            return await resp.json()


    async def get_status_sns(self) -> Return_Status_SNS | None:
        response = await self._request(command = "status", para = 8)
        data = list(response["StatusSNS"].values())
        return Return_Status_SNS(data[0], **data[-1]) if response else None

    
    async def get_power(self) -> float | None:
        data = await self.get_status_sns()
        return data.power if data else None
    
    
    async def get_energy_total_lifetime(self) -> float | None:
        data = await self.get_status_sns()
        return data.energy if data else None


    async def has_power(self) -> bool | None:
        response = await self._request(command = "status", para = 0)
        data = response["Status"]["Power"]
        return bool(data)

    
    async def is_power_on(self) -> bool | None:
        response = await self._request(command = "status", para = 0)
        data = response["Status"]["Power"] and response["Status"]["PowerOnState"]
        return bool(data)
