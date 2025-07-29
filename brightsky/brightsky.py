__doc__=""" A python library for Bright Sky weather data """
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest

from dataclasses import dataclass

from datetime import datetime

import pandas as pd

from utils.typing import Optional, Any, Dict
Return_Request = Optional[Dict[str, Any]]
    
class Sky:

    _URL, _ENDPOINT = 'api.brightsky.dev', 'weather'
    
    def __init__(self,
                 lat: float,
                 lon: float,
                 day: str,
                 tz: str = 'UTC', timeout: int = 20):
        
        self.url = f'https://{self._URL}/{self._ENDPOINT}?'
        self.url += f'lat={lat}&lon={lon}&'
        self.url += f'date={datetime.strptime(day, "%y%m%d").strftime("%Y-%m-%d")}&'
        self.url += f'tz={tz}'
        self.timeout = timeout

        
    async def _request(self) -> Return_Request:
        try:
            async with ClientSession() as ses, ses.get(
                    self.url,
                    timeout=self.timeout
            ) as resp:
                if not resp.ok:
                    raise HttpBadRequest(f"HTTP Error: {resp.status}")
                return await resp.json()
        except TimeoutError:
            logger.error('Timeout')
            return None

        
    async def _get_weather_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            logger.error('Raised unknown exception')
            return None
        return response['weather'] if response is not None else None


    async def get_sky_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_weather_info()
        except:
            logger.error('Raised unknown exception')
            return None
        if response is None:
            return None
        
        df = pd.DataFrame(response) 
        df.set_index('timestamp', inplace = True)
        skydf = df.loc[:,['sunshine', 'cloud_cover']]
        return skydf


    async def get_solar_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_weather_info()
        except:
            logger.error('Raised unknown exception')
            return None            
        if response is None:
            return None
        
        df = pd.DataFrame(response)
        df.set_index('timestamp', inplace = True)
        solardf  = df.loc[:,['solar']]
        return solardf
    

    async def _get_sources_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            logger.error('Raised unknown exception')
            return None
        return response['sources'] if response is not None else None

    
    async def get_sources_info(self) -> Optional[pd.DataFrame]:
        try:
            response = await self._get_sources_info()
        except:
            logger.error('Raised unknown exception')
            return None
        if response is None:
            return None
        
        df = pd.DataFrame(response)
        df.set_index('id', inplace = True)
        sourcesdf = df.loc[:,['distance','height','station_name']]
        return sourcesdf
