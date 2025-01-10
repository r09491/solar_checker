import sys

from ..types import (
    t64, t64s,
    f64, f64s
)

from ._get_w_line import _get_w_line
from ._get_kwh_line import _get_kwh_line
from ._get_kwh_bar_unified import _get_kwh_bar_unified
from ._get_blocks import _get_blocks

async def get_w_line(time: t64s, smp: f64s,
                     ivp1: f64s, ivp2: f64s, spph: f64s,
                     sbpi: f64s, sbpo: f64s, sbpb: f64s,
                     tphases: t64s = None):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_w_line,**vars())
    else:
        return _get_w_line(**vars())

    
async def get_kwh_line(
        time: t64s, smeon: f64s, smeoff: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh: f64s, full_kwh: f64s, price: f64,
        tphases: t64s = None,
        time_format: str = '%H:%M'):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(_get_kwh_line, **vars())
    else:
        return _get_kwh_line(**vars())

    
async def get_kwh_bar_unified(
        time: t64s, smeon: f64s, smeoff: f64s, balcony: f64s,
        price: f64, bar_width: f64, time_format:str):
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_kwh_bar_unified, **vars())
    else:
        return _get_kwh_bar_unified(**vars())


async def get_blocks(time: t64, smp: f64,
                     ivp1: f64, ivp2: f64, spph: f64,
                     sbpi: f64s, sbpo: f64s, sbpb: f64,
                     spp1: f64, spp2: f64, spp3: f64, spp4: f64):
    if sys.version_info >= (3, 9):
        return await asyncio.to_thread(_get_blocks,**vars())
    else:
        return _get_blocks(**vars())

