__doc__="""
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

from ..typing import Dict, List, strings

from pandas import(
    read_csv,
    DataFrame
)


def _get_logdays(logprefix: str,
                 logdir: str,
                 logdayformat: str = '*') -> strings:
    pattern = os.path.join(logdir, f'{logprefix}_{logdayformat}.log')
    logpaths = glob.glob(pattern)
    logfiles = [os.path.basename(lp) for lp in logpaths]
    lognames = [os.path.splitext(lf)[0] for lf in logfiles]
    logdays = [ln.replace(f'{logprefix}_', '') for ln in lognames]
    logdays.sort()
    return logdays

async def get_logdays(logprefix: str,
                      logdir: str,
                      logdayformat: str = '*') -> strings:
    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_logdays, **vars()) # type: ignore[unused-ignore]
    else:
        return _get_logdays(**vars())


def _get_log(
        logcols: list,
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:

    if logday is None and logprefix is None and logdir is None:
        logger.info(f'Reading CSV data from "stdin"')
        logfile = sys.stdin 
    else:
        logfile = os.path.join(logdir, f'{logprefix}_{logday}.log')
        logger.info(f'Reading CSV data from file "{logfile}"')
        if not os.path.isfile(logfile):
            logger.warning(f'CSV data file not found "{logfile}"')
            return None
    return read_csv(logfile, names = logcols)
    
async def get_log(
        logcols: list,
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> Dict:

    if sys.version_info >= (3, 9): 
        return await asyncio.to_thread(
            _get_log, **vars())
    else:
        return _get_log(**vars())


""" Get the list of logdays and the list of dictionaries with all the
recordings """
async def get_logs(
        logcols: list,
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str) -> List:

    """ Get the list of logdays """
    logdays = (await get_logdays(
        logcols,
        logprefix,
        logdir,
        logdayformat
    ))[-logmaxdays:]

    logtasks = [asyncio.create_task(
        get_log(
            logcols, ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logframes = await asyncio.gather(*logtasks)
    
    return logdays, logframes


""" Get the dataframe with the list of logdays and the list of
dictionaries with all the recordings """
async def get_logs_frame(
        logcols: List,
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str) -> DataFrame:
    
    logdays, logframes = await get_logs(
        logcols,
        logmaxdays,
        logdayformat,
        logprefix,
        logdir
    )
    
    return pd.DataFrame(index = logdays, data=logcols)
