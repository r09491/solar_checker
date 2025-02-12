__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

from datetime import (
    datetime,
    timedelta
    )

import pandas as pd

from .typing import t64

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
    'SBPI', 'SBPO', 'SBPB', 'SBSB',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]

""" The power names for weather forecast """
FORECAST_NAMES = POWER_NAMES[2:8]

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


PARTITION_NAMES = ['SBPI','SBPB-','SBPB+','SBPO','IVP','SMP-','SMP+']
VIEW_NAMES = ['SUN', '>BAT', 'BAT>', 'BANK', 'INV', '>GRID', 'GRID>']
PARTITION_2_VIEW = dict(zip(PARTITION_NAMES, VIEW_NAMES))


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
                        hour=dt_t.hour,
                        second=dt_t.second))

def ymd_tomorrow(today: str) -> str:
    dt_today = datetime.strptime(today, "%y%m%d")
    return (dt_today + timedelta(days=1)).strftime("%y%m%d")

def ymd_yesterday(today: str) -> str:
    dt_today = datetime.strptime(today, "%y%m%d")
    return (dt_today - timedelta(days=1)).strftime("%y%m%d")

def ymd_365_days_ahead(today: str) -> str:
    dt_today = datetime.strptime(today, "%y%m%d")
    return (dt_today + timedelta(days=365)).strftime("%y%m%d")

def ymd_365_days_ago(today: str) -> str:
    dt_today = datetime.strptime(today, "%y%m%d")
    return (dt_today - timedelta(days=365)).strftime("%y%m%d")


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
                        microsecond=999999))

def t64_h_first(t: t64) -> t64:
    dt = pd.to_datetime(str(t))
    return t64(datetime(year=dt.year,
                        month=dt.month,
                        day=dt.day,
                        minute=0,
                        hour=dt.hour,
                        second=0,
                        microsecond=0))

def t64_h_last(t: t64) -> t64:
    dt = pd.to_datetime(str(t))
    return t64(datetime(year=dt.year,
                        month=dt.month,
                        day=dt.day,
                        minute=59,
                        hour=dt.hour,
                        second=59,
                        microsecond=999999))

def t64_h_next(t: t64) -> t64:
    dt = pd.to_datetime(str(t))
    return t64(dt + timedelta(hours=1))


def t64_from_iso(value: str) -> t64:
    try:
        dt = datetime.fromisoformat(value)
    except:
        return None
    return t64_first(t64(dt))
