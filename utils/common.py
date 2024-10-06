__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

from datetime import (
    datetime,
    timedelta
    )

import pandas as pd

from .types import t64

""" The samples in the record logs """
SAMPLE_NAMES = [
    'TIME',
    'SMP', 'SME',
    'IVP1', 'IVE1', 'IVTE1',
    'IVP2', 'IVE2', 'IVTE2',
    'SPPH', 'SBPI', 'SBPO', 'SBPB', 'SBSB',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]

""" The power samples subset"""
POWER_NAMES = [
    'TIME',
    'SMP', 
    'IVP1',
    'IVP2',
    'SPPH',
    'SBPI', 'SBPO', 'SBPB',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]


"""
Only power samples may be used for predicts. For some sanmples it is
possible to split between positive and negative values.
"""
PREDICT_NAMES = [
    'SMP', 'SMP+', 'SMP-', 
    'IVP1',
    'IVP2',
    'SPPH',
    'SBPI', 'SBPO', 'SBPB', 'SBPB+','SBPB-',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]


def t64_to_hm(t: t64) -> str:
    return pd.to_datetime(str(t)).strftime("%H:%M")

""" Converts hm format to t64 """
def hm_to_t64(hm: str) -> t64:
    return t64(datetime.strptime(hm, "%H:%M"))

def ymd_over_t64(t: t64, day: str) -> t64:
    dt_day = datetime.strptime(day, "%y%m%d")
    dt_t = pd.to_datetime(str(t))
    return t64(datetime(year=dt_day.year,
                        month=dt_day.month,
                        day=dt_day.day,
                        minute=dt_t.minute,
                        hour=dt_t.hour))

def ymd_tomorrow(today: str) -> t64:
    dt_today = datetime.strptime(today, "%y%m%d")
    return (dt_today + timedelta(days=1)).strftime("%y%m%d")


def t64_clear(t: t64) -> t64:
    dt_ymd = pd.to_datetime(str(t))
    return t64(datetime(year=1954,
                        month=12,
                        day=10,
                        minute=dt_ymd.minute,
                        hour=dt_ymd.hour,
                        second=dt_ymd.second,
                        microsecond=dt_ymd.microsecond))

def t64_first(t: t64) -> t64:
    dt = pd.to_datetime(str(t))
    return t64(datetime(year=dt.year,
                        month=dt.month,
                        day=dt.day,
                        minute=dt.minute,
                        hour=dt.hour,
                        second=0,
                        microsecond=0))

def t64_last(t: t64) -> t64:
    dt = pd.to_datetime(str(t))
    return t64(datetime(year=dt.year,
                        month=dt.month,
                        day=dt.day,
                        minute=dt.minute,
                        hour=dt.hour,
                        second=59,
                        microsecond=999))



