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

from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpBadRequest


from .helpers import (
    get_headers,
    get_dot_ecoflow_api
)

class Device():
    
    def __init__(self, timeout: int = 10):
        self.url, self.key, self.secret, _ = get_dot_ecoflow_api()
        self.timeout = timeout

    
    async def _get(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.get(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

    async def _post(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.post(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

    async def _put(self, headers: dict, json: dict) -> dict:
        url, timeout = self.url, self.timeout
        async with ClientSession() as session:
            async with session.put(
                    url = url,
                    headers = headers,
                    json = json,
                    timeout = timeout
            ) as response:
                if not response.ok:
                    raise HttpBadRequest(f"HTTP Error: {response.status}")
                return await response.json()

            
    def _get_headers(self, params: dict):
        return get_headers(self.key, self.secret, params)
            
    async def get(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._get(headers=headers, json=params)

    async def post(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._post(headers=headers, json=params)

    async def put(self, params: dict = None) -> dict:
        headers = self._get_headers(params)
        return await self._put(headers=headers, json=params)
