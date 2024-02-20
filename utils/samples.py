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
            logger.warning(f'CSV data file not found "{logfile}"')
            return None
        
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPP,SBPI,SBPO,SBPB,SBSB'.split(',')
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

    """ The normalised solarbank power input """
    sbpi = np.array(df.SBPI.apply(_str2float))
    if np.isnan(sbpi).any():
        logger.warn(f'Undefined SBPI samples')
        sbpi = None

    """ The normalised solarbank power output """
    sbpo = np.array(df.SBPO.apply(_str2float))
    if np.isnan(sbpo).any():
        logger.warn(f'Undefined SBPO samples')
        spbo = None

    """ The normalised solarbank power battery """
    sbpb = np.array(df.SBPB.apply(_str2float))
    if np.isnan(sbpb).any():
        logger.warn(f'Undefined SBPB samples')
        sbpb =  None

    """ The normalised solarbank power state of charge """
    sbsb = np.array(df.SBSB.apply(_str2float))
    if np.isnan(sbsb).any():
        logger.warn(f'Undefined SBSB samples')
        sbsb = None
    
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

    logger.info(f'Reading CSV data "ok".')
    return {'TIME' : time,
            'SMP' : smp, 'IVP1' : ivp1, 'IVP2' : ivp2,
            'SME' : sme, 'IVE1' : ive1, 'IVE2' : ive2, 'SPP' : spp,
            'SBPI' : sbpi, 'SBPO' : sbpo, 'SBPB' : sbpb, 'SBSB' : sbsb}

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


async def get_kwh_sum_month(logmonth: str,
                            logprefix: str,
                            logdir: str,
                            logdayformat:str) -> dict:

    dt = datetime.strptime(logmonth, logdayformat[:-2])
    first = t64(datetime(year=dt.year,
                         month=dt.month, day=1), 'D')
    last = t64(datetime(year=dt.year+dt.month//12,
                        month=dt.month%12+1, day=1), 'D')                               
    mtime = np.arange(first, last, dtype=t64)

    async def doer(t: t64) -> dict:
        md = t.astype(datetime).strftime(logdayformat)
        ms = await get_kwh_sum_from_csv(md, logprefix, logdir)
        return ms.values()
    results = await asyncio.gather(*[doer(t) for t in mtime])
    
    msme = np.zeros(mtime.size, dtype=f64)
    mive1 = np.zeros(mtime.size, dtype=f64)
    mive2 = np.zeros(mtime.size, dtype=f64)
    mspe  = np.zeros(mtime.size, dtype=f64)
    for i, r in enumerate(results):
        msme[i], mive1[i], mive2[i], mspe[i] = r

    return {'TIME':mtime, 'SME':msme, 'IVE1':mive1, 'IVE2':mive2, 'SPE':mspe}


async def get_kwh_sum_year(logyear: str,
                           logprefix: str,
                           logdir: str,
                           logdayformat:str) -> list:

    dt = datetime.strptime(logyear, logdayformat[:2])
    first = t64(datetime(year=dt.year, month=1, day=1), 'M')
    last = t64(datetime(year=dt.year+1,month=1, day=1), 'M')
    ytime = np.arange(first, last, dtype=t64)

    async def doer(t: t64) -> dict:
        yd = t.astype(datetime).strftime(logdayformat)[:-2]
        ys = await get_kwh_sum_month(yd,logprefix,logdir,logdayformat)
        yss = [v.sum() for v in list(ys.values())[1:]]
        return yss
    results = await asyncio.gather(*[doer(t) for t in ytime])

    ysme = np.zeros(ytime.size, dtype=f64)
    yive1 = np.zeros(ytime.size, dtype=f64)
    yive2 = np.zeros(ytime.size, dtype=f64)
    yspe  = np.zeros(ytime.size, dtype=f64)

    for i, r in enumerate(results):
        ysme[i], yive1[i], yive2[i], yspe[i] = r

    return {'TIME':ytime, 'SME':ysme, 'IVE1':yive1, 'IVE2':yive2, 'SPE':yspe}        


async def get_kwh_cumsum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    c = await get_columns_from_csv(logday,logprefix, logdir)
    return {'SME' : c['SMP'].cumsum()/60.0/1000.0 if c and 'SMP' in c else 0.0,
            'IVE1' : c['IVP1'].cumsum()/60.0/1000.0 if c and 'IVE1' in c else 0.0,
            'IVE2' : c['IVP2'].cumsum()/60.0/1000.0 if c and 'IVE2' in c else 0.0,
            'SPE' : c['SPP'].cumsum()/60.0/1000.0 if c and 'SPP' in c else 0.0}


