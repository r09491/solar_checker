__doc__=""" This is a poor Tuya libray to get the latest data from a
tuya smartplug, to turn it on, to turn it off. It is tried to make the
calls asychronous.

It is heavily depenendent on the package tinytuya. Tinytuya wizard has
to be run before usage and therefor to be installed..  See the
tinytuya repository on github.com.
"""
__version__ = "0.0.2"
__author__ = "r09491@gmail.com"

import sys
import os
import json
import asyncio
import tinytuya # type: ignore

from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class Return_Config:
    id: str
    ip: str
    local_key: str
    version: str

@dataclass
class Return_Status:
    current: float
    power: float
    voltage: float

    
    
class Smartplug:

    def _get_config(self, name: str) -> Optional[Return_Config]:
        cjson = None
        home = os.path.expanduser('~')
        cnames = [".poortuya", os.path.join(home, ".poortuya" )]
        for cn in cnames:
            try:
                with open(cn, "r") as cf:
                    cjson = json.load(cf)
                    break
            except:
                pass

        return Return_Config(**cjson[name]) if cjson else None 

    
    def __init__(self, name: str, timeout: int = 10):
        self.config = self._get_config(name)
        self.timeout = timeout

        
    def _get_status(self) -> Optional[Return_Status]:
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version
        ) if self.config is not None else None
        
        status = device.status() if device is not None else None
        dps = status.get('dps') if status is not None else None

        return Return_Status(
            dps['18'],    #mA
            dps['19']/10, #W
            dps['20']/10, #V
        ) if dps is not None and dps['1'] else None

    async def get_status(self) -> Optional[Return_Status]:
        if sys.version_info >= (3, 9): 
            return await asyncio.to_thread(self._get_status) # type: ignore[unused-ignore]
        else:
            return self._get_status()

        
    def _turn_on(self) -> Any:
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version,
        ) if self.config is not None else None

        return device.turn_on() if device is not None else None 

    async def turn_on(self) -> None:
        if sys.version_info >= (3, 9): 
            await asyncio.to_thread(self._turn_on) # # type: ignore[unused-ignore]
        else:
            self._turn_on()

            
    def _turn_off(self) -> Any:
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version,
        ) if self.config is not None else None

        return device.turn_off() if device is not None else None 

    async def turn_off(self) -> None:
        if sys.version_info >= (3, 9): 
            await asyncio.to_thread(self._turn_off) # type: ignore[unused-ignore]
        else:
            self._turn_off()
