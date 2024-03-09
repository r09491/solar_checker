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

    __me__='_get_columns_from_csv'
    logger.info(f'{__me__}: started "{logday}"')

    if logday is None and logprefix is None and logdir is None:
        logger.info(f'{__me__}:Reading CSV data from "stdin"')
        logfile = sys.stdin 
    else:
        logfile = os.path.join(logdir, f'{logprefix}_{logday}.log')
        logger.info(f'Reading CSV data from file "{logfile}"')
        if not os.path.isfile(logfile):
            logger.warning(f'{__me__}:CSV data file not found "{logfile}"')
            return None
        
    sep = ','
    names = 'TIME,SMP,SME,IVP1,IVE1,IVTE1,IVP2,IVE2,IVTE2,SPPH,SBPI,SBPO,SBPB,SBSB,SPP1,SPP2,SPP3,SPP4'.split(',')
    df = read_csv(logfile, sep=sep, names=names)

    """ The timestamps """
    time = np.array(df.TIME.apply(_iso2date))

    """ The smartmeter power samples """
    smp = np.array(df.SMP.apply(_str2float))
    if np.isnan(smp).any():
        logger.error(f'{__me__}:Undefined SMP samples')
        return None
    
    """ The normalised inverter power samples channel 1 """
    ivp1 = np.array(df.IVP1.apply(_str2float))
    if np.isnan(ivp1).any():
        logger.error(f'{__me__}:Undefined IVP1 samples')
        return None

    """ The normalised inverter power samples channel 2 """
    ivp2 = np.array(df.IVP2.apply(_str2float))
    if np.isnan(ivp2).any():
        logger.error(f'{__me__}:Undefined IVP2 samples')
        return None

    """ The normalised smartmeter energy samples """
    sme = np.array(df.SME.apply(_str2float))
    if np.isnan(sme).any():
        logger.error(f'{__me__}:Undefined SME samples')
        return None
    
    """ The normalised inverter energy samples channel 1 """
    ive1 = np.array(df.IVE1.apply(_str2float))
    if np.isnan(ive1).any():
        logger.error(f'{__me__}:Undefined IVE2 samples')
        return None
    
    """ The normalised inverter energy samples channel 2 """
    ive2 = np.array(df.IVE2.apply(_str2float))
    if np.isnan(ive2).any():
        logger.error(f'{__me__}:Undefined IVE2 samples')
        return None

    """ The normalised smartplug power home"""
    spph = np.array(df.SPPH.apply(_str2float))
    if np.isnan(spph).any():
        logger.error(f'{__me__}:Undefined SPPH samples')
        return None

    """ The normalised solarbank power input """
    sbpi = np.array(df.SBPI.apply(_str2float))
    if np.isnan(sbpi).any():
        logger.warn(f'{__me__}:Undefined SBPI samples')
        sbpi = None

    """ The normalised solarbank power output """
    sbpo = np.array(df.SBPO.apply(_str2float))
    if np.isnan(sbpo).any():
        logger.warn(f'{__me__}:Undefined SBPO samples')
        spbo = None

    """ The normalised solarbank power battery """
    sbpb = np.array(df.SBPB.apply(_str2float))
    if np.isnan(sbpb).any():
        logger.warn(f'{__me__}:Undefined SBPB samples')
        sbpb =  None

    """ The normalised solarbank power state of charge """
    sbsb = np.array(df.SBSB.apply(_str2float))
    if np.isnan(sbsb).any():
        logger.warn(f'{__me__}:Undefined SBSB samples')
        sbsb = None

    """ The normalised smartplug power switch 1 """
    spp1 = np.array(df.SPP1.apply(_str2float))
    if np.isnan(spp1).any():
        logger.warn(f'{__me__}:Undefined SPP1 samples')
        spp1 =  None

    """ The normalised smartplug power switch 2 """
    spp2 = np.array(df.SPP2.apply(_str2float))
    if np.isnan(spp2).any():
        logger.warn(f'{__me__}:Undefined SPP2 samples')
        spp2 =  None

    """ The normalised smartplug power switch 3 """
    spp3 = np.array(df.SPP3.apply(_str2float))
    if np.isnan(spp3).any():
        logger.warn(f'{__me__}:Undefined SPP3 samples')
        spp3 =  None

    """ The normalised smartplug power switch 3 """
    spp4 = np.array(df.SPP4.apply(_str2float))
    if np.isnan(spp4).any():
        logger.warn(f'{__me__}:Undefined SPP4 samples')
        spp4 =  None
        
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

    logger.info(f'{__me__}: done')
    return {'TIME' : time,
            'SMP' : smp, 'IVP1' : ivp1, 'IVP2' : ivp2,
            'SME' : sme, 'IVE1' : ive1, 'IVE2' : ive2, 'SPPH' : spph,
            'SBPI' : sbpi, 'SBPO' : sbpo, 'SBPB' : sbpb, 'SBSB' : sbsb,
            'SPP1' : spp1, 'SPP2' : spp2, 'SPP3' : spp3, 'SPP4' : spp4}

async def get_columns_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_columns_from_csv, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_columns_from_csv(**vars())

"""
Calculates the energy in kWH for each column in the record file    
"""
async def get_kwh_sum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:

    __me__='get_kwh_sum_month'
    logger.info(f'{__me__}: started "{logday}"')
    c = await get_columns_from_csv(logday,logprefix, logdir)
    logger.info(f'{__me__}: done')
 
    smp = c['SMP'] if c and 'SMP' in c else None

    smpon = np.zeros_like(smp) if smp is not None else None
    if smpon is not None:
        issmpon = smp>0
        smpon[issmpon] = smp[issmpon]
        
    smpoff = np.zeros_like(smp) if smp is not None else None
    if smpoff is not None:
        issmpoff = smp<=0
        smpoff[issmpoff] = smp[issmpoff]

    return {'SMEON'  : smpon.sum()/60.0/1000.0 if smpon is not None else 0.0,
            'SMEOFF' : smpoff.sum()/60.0/1000.0 if smpoff is not None else 0.0,
            'IVE1'   : c['IVP1'].sum()/60.0/1000.0 if c and 'IVP1' in c else 0.0,
            'IVE2'   : c['IVP2'].sum()/60.0/1000.0 if c and 'IVP2' in c else 0.0,
            'SPEH'   : c['SPPH'].sum()/60.0/1000.0 if c and 'SPPH' in c else 0.0,
            'SBEO'   : c['SBPO'].sum()/60.0/1000.0 if c and 'SBPO' in c else 0.0}


"""
Calculates the energy in kWH for each day of the specified month. Each
day has a list of energies. Dependent on the configuration not all
items may have recorded data for each day. Data may be recorded on
different and the same days with different devices. So one values may
not show the complete accumulated energy.
"""
async def get_kwh_sum_month(logmonth: str,
                            logprefix: str,
                            logdir: str,
                            logdayformat:str) -> dict:

    __me__='get_kwh_sum_month'
    logger.info(f'{__me__}: started "{logmonth}"')

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
    
    msmeon = np.zeros(mtime.size, dtype=f64)
    msmeoff = np.zeros(mtime.size, dtype=f64)
    mive1 = np.zeros(mtime.size, dtype=f64)
    mive2 = np.zeros(mtime.size, dtype=f64)
    mspeh  = np.zeros(mtime.size, dtype=f64)
    msbeo  = np.zeros(mtime.size, dtype=f64)
    for i, r in enumerate(results):
        msmeon[i], msmeoff[i], mive1[i], mive2[i], mspeh[i], msbeo[i] = r

    logger.info(f'{__me__}: done')       
    return {'TIME':mtime, 'SMEON':msmeon, 'SMEOFF':msmeoff,
            'IVE1':mive1, 'IVE2':mive2, 'SPEH':mspeh, 'SBEO':msbeo}

"""
Unifies the calculated energy results for each day of the specified
month. For each day one device column is selected best representing
the energy production at that day. If connected the smartplug has
priority 1 if it directly connects an inverter to the house.  Priority
2 has the inverter if data are available. Priority 3 has the
solarbank.
"""
async def get_kwh_sum_month_unified(
        logmonth: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> dict:

    __me__='get_kwh_sum_month_unified'
    logger.info(f'{__me__}: started "{logmonth}"')

    mkwhs = await get_kwh_sum_month(
        logmonth, logprefix, logdir, logdayformat)
    mtime, msmeon, msmeoff, mive1, mive2, mspeh, msbeo = mkwhs.values()

    # 1.Prio
    umkwhs = mspeh.copy()

    # 2.Prio 
    mive = mive1 + mive2
    isive = mive>0 & ~(umkwhs>0)
    umkwhs[isive] = mive[isive]

    # 3.Prio
    issbeo = msbeo>0 & ~(umkwhs>0)
    umkwhs[issbeo] = msbeo[issbeo]

    logger.info(f'{__me__}: started')
    return {'TIME':mtime, 'SMEON':msmeon, 'SMEOFF':msmeoff,'PANEL':umkwhs}
    

"""
Calculates the energy in kWH for each month of the specified
year. Each month has a list of energies. Dependent on the
configuration not all items may have recorded data for each
month. Data may be recorded on different month with different
devices. During a month the energy may be recorded by different
devices. So the columns may not show the complete energy.
"""
async def get_kwh_sum_year(
        logyear: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> list:

    __me__='get_kwh_sum_year'
    logger.info(f'{__me__}: started "{logyear}"')

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

    ysmeon = np.zeros(ytime.size, dtype=f64)
    ysmeoff = np.zeros(ytime.size, dtype=f64)
    yive1 = np.zeros(ytime.size, dtype=f64)
    yive2 = np.zeros(ytime.size, dtype=f64)
    yspeh  = np.zeros(ytime.size, dtype=f64)
    ysbeo  = np.zeros(ytime.size, dtype=f64)

    for i, r in enumerate(results):
        ysmeon[i], ysmeoff[i], yive1[i], yive2[i], yspeh[i], ysbeo[i] = r

    logger.info(f'{__me__}: done')        
    return {'TIME':ytime, 'SMEON':ysmeon, 'SMEOFF':ysmeoff,
            'IVE1':yive1, 'IVE2':yive2, 'SPEH':yspeh, 'SBEO':ysbeo}        


"""
Unifies the Calculated energy in kWH for each month of the specified
year.
"""
async def get_kwh_sum_year_unified(
        logyear: str,
        logprefix: str,
        logdir: str,
        logdayformat:str) -> list:

    __me__='get_kwh_sum_year_unified'
    logger.info(f'{__me__}: started "{logyear}"')

    dt = datetime.strptime(logyear, logdayformat[:2])
    first = t64(datetime(year=dt.year, month=1, day=1), 'M')
    last = t64(datetime(year=dt.year+1,month=1, day=1), 'M')
    ytime = np.arange(first, last, dtype=t64)

    async def doer(t: t64) -> dict:
        yd = t.astype(datetime).strftime(logdayformat)[:-2]
        ys = await get_kwh_sum_month_unified(
            yd, logprefix,logdir,logdayformat)
        yss = [v.sum() for v in list(ys.values())[1:]]
        return yss
    results = await asyncio.gather(*[doer(t) for t in ytime])

    ysmeon = np.zeros(ytime.size, dtype=f64)
    ysmeoff = np.zeros(ytime.size, dtype=f64)
    ypanel = np.zeros(ytime.size, dtype=f64)

    for i, r in enumerate(results):
        ysmeon[i], ysmeoff[i], ypanel[i] = r

    logger.info(f'{__me__}: done')        
    return {'TIME':ytime, 'SMEON':ysmeon, 'SMEOFF':ysmeoff,'PANEL':ypanel}        


async def get_kwh_cumsum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    c = await get_columns_from_csv(logday,logprefix, logdir)
    return {'SME' : c['SMP'].cumsum()/60.0/1000.0 if c and 'SMP' in c else 0.0,
            'IVE1' : c['IVP1'].cumsum()/60.0/1000.0 if c and 'IVE1' in c else 0.0,
            'IVE2' : c['IVP2'].cumsum()/60.0/1000.0 if c and 'IVE2' in c else 0.0,
            'SPEH' : c['SPPH'].cumsum()/60.0/1000.0 if c and 'SPPH' in c else 0.0,
            'SBEO' : c['SBPO'].cumsum()/60.0/1000.0 if c and 'SBPO' in c else 0.0}
