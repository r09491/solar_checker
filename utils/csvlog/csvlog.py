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
async def get_tunnel_logdays(
        logwindow:int,
        logprefix: str,
        logdir: str
) -> strings:
    # Get the list of of reversed logdays
    rlds = (await get_logdays(
        logprefix = logprefix,
        logdir = logdir,
    )) [::-1]
    # Extract the list of periodic windows
    wlds = [rlds[max(0,d-logwindow):min(len(rlds),d+logwindow+1)]
            for d,rld in enumerate(rlds) if rld[2:] == rlds[0][2:]]
    return [d for l in wlds for d in l][::-1]    


def _get_log(
        logday: str,
        logprefix: str,
        logdir: str
) -> DataFrame:

    if (logday is None) or (logprefix is None) or (logdir is None):
        logger.info(f'Reading CSV data from "stdin"')
        try:
            samples = read_csv(sys.stdin, header=None)
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
            # We cannot make any assumption about the number of rows
            samples = read_csv(logname, header=None)
        except:
            logger.error(f'Erroneous CSV data file "{logname}"')
            return None

    # With time new samples were added to the
    # right. Name the remaining column names!
    samples.columns = SAMPLE_NAMES[:len(samples.columns)]
    samples = samples[samples.columns]

    # Cleanup
    time = samples['TIME'].apply(t64_first)
    # All colums but TIME are float
    columns = samples.iloc[:,1:].astype(float)        

    # TIME must not be index!
    
    return concat(
        [time,columns], axis=1
    ).drop_duplicates(
        'TIME', keep='first'
    )


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
    if log is None:
        return None
    
    log = log[list(set(log.columns) & set(SAMPLE_NAMES))]
    return log


async def get_power_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:

    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir)
    if log is None:
        return None
    
    log = log[list(set(log.columns) & set(POWER_NAMES))]
    return log


async def get_predict_power_log(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:
    
    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir)
    if log is None:
        return None
    
    log = log[list(set(log.columns) & set(PREDICT_POWER_NAMES))]
    return log


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

    logs = [log[list(
        set(log.columns) & set(usecols)
    )] for log in logs if log is not None]

    return logdays, logs


""" Get the list of logdays and the list of dataframes with the
required recordings """
async def get_tunnel_logs(
        logwindow: int,
        logprefix: str,
        logdir: str,
        usecols: str = POWER_NAMES
) -> (List[str], List[DataFrame]):

    """ Get the list of logdays """
    logdays = await get_tunnel_logdays(
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

    logs = [log[list(
        set(log.columns) & set(usecols)
    )] for log in logs if log is not None]

    return logdays, logs


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


""" Get the dataframe with the list of tunnel logdays and the list
of dataframes with the required recordings """
async def get_tunnel_logs_df(
        logwindow: int,
        logprefix: str,
        logdir: str,
        usecols:str = POWER_NAMES,
) -> DataFrame:

    days, logs = await get_tunnel_logs(
        logwindow,
        logprefix,
        logdir,
        usecols
    )
    return concat(logs, keys=days)
