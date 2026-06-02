__doc__=""" A python library for Bright Sky weather data """
__version__ = "0.0.1"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

from aiohttp import ClientSession

from dataclasses import dataclass

from datetime import datetime

import pandas as pd

from utils.typing import Optional, Any, Dict
Return_Request = Optional[Dict[str, Any]]

TIMEOUT = 10

#SOURCE_ID = '7201'
#SOURCE_ID = '7201,61372'
#SOURCE_ID = '61372,7201'
TZ = 'Europe/Berlin'


class Sky:

    _URL, _ENDPOINT = 'api.brightsky.dev', 'weather'

    def __init__(self,
                 lat: float,
                 lon: float,
                 day: str,
                 tz: str = TZ,
                 #source_id: str = SOURCE_ID,
                 timeout: int = TIMEOUT):
        
        self.url = f'https://{self._URL}/{self._ENDPOINT}?'
        self.url += f'lat={lat}&lon={lon}&'
        self.url += f'date={datetime.strptime(day, "%y%m%d").strftime("%Y-%m-%d")}&'
        #self.url += f'source_id={SOURCE_ID}&'
        self.url += f'tz={tz}'
        self.timeout = timeout

        
    async def _request(self) -> Return_Request:
        try:
            async with ClientSession() as ses, ses.get(
                    self.url,
                    timeout=self.timeout
            ) as resp:
                return await resp.json() if resp.ok else None
        except TimeoutError:
            logger.error('Timeout')
            return None

        
    async def _get_weather_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            logger.error('Raised unknown exception')
            return None
        weather = response['weather'] if response is not None else None
        return weather


    async def get_sunshine_info(self) -> Optional[pd.DataFrame]:
        try:
            weather = await self._get_weather_info()
        except:
            logger.error('Raised unknown exception')
            return None
        if weather is None:
            logger.error('No weather for sunshine info')
            return None
        
        df = pd.DataFrame(weather)
        index = pd.to_datetime(df['timestamp'])
        df.drop('timestamp', inplace=True, axis=1)
        df.set_index(index, inplace = True)
        skydf = df.loc[:,['sunshine', 'cloud_cover']]
        return None if skydf.empty else skydf.dropna().astype(int)

    
    async def get_ai_feature_info(self) -> Optional[pd.DataFrame]:
        try:
            weather = await self._get_weather_info()
        except:
            logger.error('Raised unknown exception')
            return None
        if weather is None:
            logger.error('No weather for AI features')
            return None

        df = pd.DataFrame(weather)
        index = pd.to_datetime(df['timestamp'])
        df.drop('timestamp', inplace=True, axis=1)
        df.set_index(index, inplace = True)
        aidf = df.loc[:,['cloud_cover',
                         'temperature',
                         'dew_point',
                         'visibility'
                         ]
                      ]
        return None if aidf.empty else aidf.astype(int)
    

    async def get_cloud_info(self) -> Optional[pd.DataFrame]:
        try:
            weather = await self._get_weather_info()
        except:
            logger.error('Raised unknown exception')
            return None            
        if weather is None:
            logger.error('No weather for solar info')
            return None
        
        df = pd.DataFrame(weather)
        index = pd.to_datetime(df['timestamp'])
        df.drop('timestamp', inplace=True, axis=1)
        df.set_index(index, inplace = True)
        clouddf  = df.loc[:,['cloud_cover',
                             'temperature'
                             ]
                          ]
        return None if clouddf.empty else clouddf.astype(int)
    

    async def _get_sources_info(self) -> Optional[Dict[str, Any]]:
        try:
            response = await self._request()
        except:
            logger.error('Raised unknown exception')
            return None
        sources = response['sources'] if response is not None else None
        return sources

    
    async def get_sources_info(self) -> Optional[pd.DataFrame]:
        try:
            sources = await self._get_sources_info()
        except:
            logger.error('Raised unknown exception')
            return None
        if sources is None:
            logger.error('No response for sources')
            return None

        df = pd.DataFrame(sources)
        df.set_index('id', inplace = True)
        sourcesdf = df.loc[:,['station_name']]
        return None if sourcesdf.empty else sourcesdf
