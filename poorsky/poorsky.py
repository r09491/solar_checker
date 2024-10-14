__doc__=""" A python library for the APsystems API in local mode

Heavily influenced by the the github APsystems EZ1 repository
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest

from dataclasses import dataclass

import pandas as pd

import sys
if sys.version_info >= (3, 9): 
    from typing import Optional, Any
    Return_Request = Optional[dict[str, Any]]
else:
    from typing import Optional, Any, Dict
    Return_Request = Optional[Dict[str, Any]]

class Sky:

    _URL, _ENDPOINT = 'api.brightsky.dev', 'weather'
    
    def __init__(self, lat: float, lon: float, date: str, timeout: int = 10):
        self.url = f'https://{self._URL}/{self._ENDPOINT}?lat={lat}&lon={lon}&date={date}'
        self.timeout = timeout

        
    async def _request(self) -> Return_Request:
        try:
            async with ClientSession() as ses, ses.get(self.url,
                                                       timeout=self.timeout) as resp:
                if not resp.ok:
                    raise HttpBadRequest(f"HTTP Error: {resp.status}")
                return await resp.json()
        except:
            return None

        
    async def _get_weather_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            respone = None
        return response['weather']


    async def get_sky_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_weather_info()
        except:
            respone = None

        df = pd.DataFrame(response)
        df.set_index('timestamp', inplace = True)
        return df.loc[:,['sunshine', 'cloud_cover']]


    async def get_solar_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_weather_info()
        except:
            respone = None            

        df = pd.DataFrame(response)
        df.set_index('timestamp', inplace = True)
        return df.loc[:,['solar']]
    

    async def _get_sources_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            respone = None
        return response['sources']

    
    async def get_sources_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_sources_info()
        except:
            respone = None

        df = pd.DataFrame(response)
        df.set_index('id', inplace = True)
        return df.loc[:,['distance','station_name']]
