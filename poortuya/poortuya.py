__doc__=""" This is a poor Tuya libray to get the latest data from a
tuya smartplug, to turn it on, or to turn it off. It is tried to make
the calls asynchronously.

It is heavily depenendent on the package tinytuya. Tinytuya wizard has
to be run before usage and therefor to be installed.  See the tinytuya
repository on github.com.
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

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

@dataclass
class Return_Config:
    id: str
    ip: str
    local_key: str
    version: str

@dataclass
class Return_Status:
    closed: bool
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

    
    def __init__(self, name: str, timeout: int = 10, persist: bool = False):
        self.config = self._get_config(name)
        self.name = name
        self.timeout = timeout
        self.persist = persist


    async def get_status(self) -> Optional[Return_Status]:
        await asyncio.sleep(1) # Switch context. Allow others!
        """ 
        This is blocking call if device not plugged in.
        Timeout does not work. Also for calls below!
        """
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version,
            connection_timeout = self.timeout,
            persist = self.persist,
        ) if self.config else None
        await asyncio.sleep(1) # Switch context. Allow others!

        status = device.status() if device else None    
        dps = status.get('dps') if status else None
        return Return_Status(
            dps['1'],     #closed True
            dps['18'],    #mA
            dps['19']/10, #W
            dps['20']/10, #V
        ) if dps is not None else None

    
    async def is_switch_closed(self) -> Optional[bool]:
        status = await self.get_status()
        return status.closed if status else None

    
    async def turn_on(self) -> Optional[bool]:
        await asyncio.sleep(1)
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version,
            connection_timeout = self.timeout,
            persist = self.persist,
        ) if self.config else None
        await asyncio.sleep(1)
        result = device.turn_on() if device else None
        dps = result.get('dps') if result else None
        onoff = bool(dps['1']) if dps else None
        return onoff

    
    async def turn_off(self) -> Optional[bool]:
        await asyncio.sleep(1)
        device = tinytuya.OutletDevice(
            dev_id = self.config.id,
            address = self.config.ip,
            local_key = self.config.local_key,
            version = self.config.version,
            connection_timeout = self.timeout,
            persist = self.persist,
        ) if self.config else None
        await asyncio.sleep(1)
        result = device.turn_off() if device else None
        dps = result.get('dps') if result else None
        onoff = bool(dps['1']) if dps else None
        return onoff
