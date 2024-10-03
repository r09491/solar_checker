__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

from datetime import datetime

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
    'SBPI', 'SBPO', 'SBPB', 'SBSB',
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


""" Converts hm format to t64 """
def hm2time(hm: str) -> t64:
    return t64(datetime.strptime(hm, "%H:%M"))

