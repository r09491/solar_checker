import sys
import os.path
import glob

from datetime import datetime

from pandas import read_csv
import numpy as np

import asyncio

from .types import f64, f64s, t64, t64s, strings
    
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(__file__))
    
    
def _get_logdays(logprefix: str, logdir: str) -> strings:
    pattern = os.path.join(logdir, f'{logprefix}_*.log')
    logpaths = glob.glob(pattern)
    logfiles = [os.path.basename(lp) for lp in logpaths]
    lognames = [os.path.splitext(lf)[0] for lf in logfiles]
    logdays = [ln.replace(f'{logprefix}_', '') for ln in lognames]
    logdays.sort()
    return logdays

async def get_logdays(logprefix: str, logdir: str) -> strings:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_logdays, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_logdays(**vars())
    

def _iso2date(value: str) -> t64:
    try:
        dt = datetime.fromisoformat(value)
    except:
        return None
    return t64(datetime(year=1900,
                        month=1, day=1, minute=dt.minute, hour=dt.hour))

def _hm2date(value: str) -> t64:
    dt = datetime.strptime(value,"%H:%M")
    return t64(datetime(year=1900,
                        month=1, day=1, minute=dt.minute, hour=dt.hour))

def _str2float(value: str) -> f64:
    try:
        return f64(value)
    except:
        return None

def _get_columns_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:

    if logday is None and logprefix is None and logdir is None:
        logger.info(f'Reading CSV data from "stdin"')
        logfile = sys.stdin 
    else:
        logfile = os.path.join(logdir, f'{logprefix}_{logday}.log')
        logger.info(f'Reading CSV data from file "{logfile}"')
        if not os.path.isfile(logfile):
            return None
        
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPP'.split(',')
    df = read_csv(logfile, sep=sep, names=names)

    """ The timestamps """
    time = np.array(df.TIME.apply(_iso2date))

    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(_str2float))
    if np.isnan(smp).any():
        logger.error(f'Undefined SMP samples')
        return None
    
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(_str2float))
    if np.isnan(ivp1).any():
        logger.error(f'Undefined IVP1 samples')
        return None

    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(_str2float))
    if np.isnan(ivp2).any():
        logger.error(f'Undefined IVP2 samples')
        return None

    """ The normalised smartmeter energy samples """
    sme = np.array(df.SME.apply(_str2float))
    if np.isnan(sme).any():
        logger.error(f'Undefined SME samples')
        return None
    
    """ The normalised inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(_str2float))
    if np.isnan(ive1).any():
        logger.error(f'Undefined IVE2 samples')
        return None
    
    """ The normalised inverter energy samples channel 2 """
    ive2 = np.array(df.IVE2.apply(_str2float))
    if np.isnan(ive2).any():
        logger.error(f'Undefined IVE2 samples')
        return None

    """ The normalised smartplug power """
    spp = np.array(df.SPP.apply(_str2float))
    if np.isnan(spp).any():
        logger.error(f'Undefined SPP samples')
        return None
    
    # Get rid of offsets and fill tails

    sme -= sme[0]
    sme[sme<0.0] = 0.0
    sme[np.argmax(sme)+1:] = sme[np.argmax(sme)]

    ive1[ive1<0.0] = 0.0
    ive1 -= ive1[0]
    ive1[np.argmax(ive1)+1:] = ive1[np.argmax(ive1)]

    ive2 -= ive2[0]
    ive2[ive2<0.0] = 0.0
    ive2[np.argmax(ive2)+1:] = ive2[np.argmax(ive2)]

    logger.info(f'Reading CSV data done')
    return {'TIME' : time,
            'SMP' : smp, 'IVP1' : ivp1, 'IVP2' : ivp2,
            'SME' : sme, 'IVE1' : ive1, 'IVE2' : ive2,
            'SPP' : spp}

async def get_columns_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_columns_from_csv, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_columns_from_csv(**vars())


async def get_kwh_sum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    c = await get_columns_from_csv(logday,logprefix, logdir)
    return {'SME' : c['SMP'].sum()/60.0/1000.0 if c and 'SMP' in c else 0.0,
            'IVE1' : c['IVP1'].sum()/60.0/1000.0 if c and 'IVE1' in c else 0.0,
            'IVE2' : c['IVP2'].sum()/60.0/1000.0 if c and 'IVE2' in c else 0.0,
            'SPE' : c['SPP'].sum()/60.0/1000.0 if c and 'SPP' in c else 0.0}

async def get_kwh_cumsum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    c = await get_columns_from_csv(logday,logprefix, logdir)
    return {'SME' : c['SMP'].cumsum()/60.0/1000.0 if c and 'SMP' in c else 0.0,
            'IVE1' : c['IVP1'].cumsum()/60.0/1000.0 if c and 'IVE1' in c else 0.0,
            'IVE2' : c['IVP2'].cumsum()/60.0/1000.0 if c and 'IVE2' in c else 0.0,
            'SPE' : c['SPP'].cumsum()/60.0/1000.0 if c and 'SPP' in c else 0.0}
