pp__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import sys
import os.path
import glob
import asyncio

from ..typing import(
    f64, t64, Dict, List, strings
)
from ..common import(
    POWER_NAMES,
    PREDICT_POWER_NAMES,
    SAMPLE_NAMES,
    t64_first,
    ymd_today,
    ymd_yesterday
)
from pandas import(
    DataFrame,
    read_csv,
    concat
)


CACHE = dict()

def cache(f):

    async def wrapper(
            logday: str,
            logprefix: str,
            logdir: str
    ) -> DataFrame:

        if ((logday is None) or
            (logday == ymd_today())
        ):
            logger.info(f'New values without store for "{logday}"')
            data = await f(
                logday,
                logprefix,
                logdir
            )
            return data
        
        if ((logday in CACHE) and
            ((logday != ymd_yesterday(ymd_today())) or
             (CACHE[logday] is not None))
        ):
            logger.info(f'Using values of "{logday}" from cache')
            data = CACHE[logday]
            await asyncio.sleep(0)
            return data
        
        data = await f(
            logday,
            logprefix,
            logdir
        )
        logger.info(f'Store and use values of "{logday}" in cache')
        CACHE[logday] = data
        return data

    return wrapper


def _get_logdays(
        logprefix: str,
        logdir: str,
        logdayformat: str = '*'
) -> strings:
    pattern = os.path.join(logdir, f'{logprefix}_{logdayformat}.log')
    logpaths = glob.glob(pattern)
    logfiles = [os.path.basename(lp) for lp in logpaths]
    lognames = [os.path.splitext(lf)[0] for lf in logfiles]
    logdays = [ln.replace(f'{logprefix}_', '') for ln in lognames]
    logdays.sort()
    return logdays

async def get_logdays(
        logprefix: str,
        logdir: str,
        logdayformat: str = '*'
) -> strings:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread( _get_logdays, **vars())
    else:
        return _get_logdays(**vars())

""" Return the logdays from the windows in each year relative from
'today'.  'today' is the last item in the retuned list """
async def get_windowed_logdays(
        logwindow:int,
        logprefix: str,
        logdir: str
) -> list[str]:
    # Get the list of of reversed logdays
    rlds = (await get_logdays(
        logprefix = logprefix,
        logdir = logdir
    )) [::-1]
    # Extract the list of periodic windows
    wlds = [rlds[max(0,d-logwindow):min(len(rlds),d+logwindow)]
            for d,_ in enumerate(rlds) if d%366 == 0]
    # Return the flattened list of days
    return [d for l in wlds for d in l][::-1]    


def _get_log(
        logday: str,
        logprefix: str,
        logdir: str
) -> DataFrame:

    if (logday is None) or (logprefix is None) or (logdir is None):
        logger.info(f'Reading CSV data from "stdin"')
        try:
            samples = read_csv(
                sys.stdin,
                names = SAMPLE_NAMES,
                #usecols = usecols,
                parse_dates=["TIME"],
                dtype="float64"
            )
        except:
            logger.error(f'Erroneous CSV data from "stdin"')
            return None
        
    else:
        logname = os.path.join(logdir, f'{logprefix}_{logday}.log')
        logger.info(f'Reading CSV data from file "{logname}"')
        if not os.path.isfile(logname):
            logger.warning(f'CSV data file not found "{logname}"')
            return None

        try:
            with open(logname, 'r') as logfile:
                samples = read_csv(
                    logfile,
                    names = SAMPLE_NAMES,
                    #usecols = usecols,
                    parse_dates=["TIME"],
                    dtype="float64"
                )
        except:
            logger.error(f'Erroneous CSV data file "{logname}"')
            return None
        
    try:        
        samples['TIME'] = samples['TIME'].apply(t64_first)
    except:
        logger.error(f'Problem in TIME column of "{logname}"')
        return None
    
    samples.drop_duplicates(inplace = True)
    samples.fillna(0.0, inplace = True)

    return samples

@cache
async def get_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None
) -> DataFrame:

    if sys.version_info >= (3, 9): 
        log = await asyncio.to_thread(_get_log, **vars())
        await asyncio.sleep(0.1)
    else:
        log = _get_log(**vars())

    return log

async def get_sample_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:

    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir)
    
    return log[SAMPLE_NAMES] if log is not None else None

async def get_power_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:

    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir)
    
    return log[POWER_NAMES] if log is not None else None

async def get_predict_power_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:
    
    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir)
    
    return log[PREDICT_POWER_NAMES] if log is not None else None


""" Get the list of logdays and the list of dataframes with the
required recordings """
async def get_logs(
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        usecols: str = POWER_NAMES
) -> (List[str], List[DataFrame]):

    """ Get the list of logdays """
    logdays = (await get_logdays(
        logprefix,
        logdir,
        logdayformat
    ))[-logmaxdays:]

    logtasks = [asyncio.create_task(
        get_log(
            ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logs = await asyncio.gather(*logtasks)
    
    return logdays, [log[usecols] for log in logs if log is not None]


""" Get the list of logdays and the list of dataframes with the
required recordings """
async def get_windowed_logs(
        logwindow: int,
        logprefix: str,
        logdir: str,
        usecols: str = POWER_NAMES
) -> (List[str], List[DataFrame]):

    """ Get the list of logdays """
    logdays = await get_windowed_logdays(
        logwindow,
        logprefix,
        logdir,
    )

    logtasks = [asyncio.create_task(
        get_log(
            ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logs = await asyncio.gather(*logtasks)
    
    return logdays, [log[usecols] for log in logs if log is not None]


""" Get the dataframe with the list of logdays and the list of
dataframes with the required recordings """
async def get_logs_df(
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str,
        usecols:str = POWER_NAMES,
) -> DataFrame:

    days, logs = await get_logs(
        logmaxdays,
        logdayformat,
        logprefix,
        logdir,
        usecols
    )
    return concat(logs, keys=days)


""" Get the dataframe with the list of windowed logdays and the list
of dataframes with the required recordings """
async def get_windowed_logs_df(
        logwindow: int,
        logprefix: str,
        logdir: str,
        usecols:str = POWER_NAMES,
) -> DataFrame:

    days, logs = await get_windowed_logs(
        logwindow,
        logprefix,
        logdir,
        usecols
    )
    return concat(logs, keys=days)
