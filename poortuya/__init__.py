__doc__=""" This is a poor Tuya libray to get the latest data from a
tuya smartplug, to turn it on, to turn it off. It is tried to make the
calls asychronous.

It is heavily depenendent on the package tinytuya. Tinytuya wizard has
to be run before usage and therefor to be installed..  See the
tinytuya repository on github.com.
"""
__version__ = "0.0.2"
__author__ = "r09491@t-online.de"

import sys
import asyncio
import tinytuya

from dataclasses import dataclass

@dataclass
class Return_Status:
    current: float
    power: float
    voltage: float

    
class Smartplug:

    def __init__(self, ip_address: str, port: int = 80, timeout: int = 10):
        #TODO Read from file
        self.id = "bf444d8065dfe2f9ba5mx5"
        self.local_key = "f750965f93818cb6"
        self.version = 3.3

        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout

        
    def _get_status(self) -> Return_Status:
        device = tinytuya.OutletDevice(
            dev_id = self.id,
            address = self.ip_address,
            local_key = self.local_key,
            version = self.version, )
        status = device.status()
        dps = status ['dps'] if 'dps' in status else None
        return Return_Status(
            dps['18'],    #mA
            dps['19']/10, #W
            dps['20']/10, #V
        ) if dps is not None and dps['1'] else None

    async def get_status(self) -> Return_Status:
        if sys.version_info.major == 3 and sys.version_info.minor >= 9: 
            return await asyncio.to_thread(self._get_status)
        else:
            return await self._get_status()

    def _turn_on(self):
        device = tinytuya.OutletDevice(
            dev_id = self.id,
            address = self.ip_address,
            local_key = self.local_key,
            version = self.version, )
        status = device.status()
        device.turn_on()

    async def turn_on(self):
        if sys.version_info.major == 3 and sys.version_info.minor >= 9: 
            await asyncio.to_thread(self._turn_on)
        else:
            await self._turn_on()
        
    def _turn_off(self):
        device = tinytuya.OutletDevice(
            dev_id = self.id,
            address = self.ip_address,
            local_key = self.local_key,
            version = self.version, )
        status = device.status()
        device.turn_on()

    async def turn_off(self):
        if sys.version_info.major == 3 and sys.version_info.minor >= 9: 
            await asyncio.to_thread(self._turn_off)
        else:
            await self._turn_off()
