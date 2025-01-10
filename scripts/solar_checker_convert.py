#!/usr/bin/env python3

__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

#from tabulate import tabulate

import numpy as np
import pandas as pd
pd.options.display.float_format = '{:,.1f}'.format
        
from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.typing import (
    t64, f64, Any, Optional, List, Dict
)
from utils.common import (
    hm_to_t64
)
from utils.samples import (
    get_logdays,
    get_columns_from_csv
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


    
@dataclass
class Script_Arguments:
    logdayformat: str
    logprefix: str
    logdir: str
    logtz: str
    

def parse_arguments() -> Script_Arguments:
    description='Convert time column to UTC'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)

    parser.add_argument(
        '--logdayformat', type=str,
        help = "Days to which to find the closest")
    
    parser.add_argument(
        '--logprefix', type=str,
        help = "The prefix used in log file names")

    parser.add_argument(
        '--logdir', type=str,
        help = "The directory the logfiles are stored")
    
    parser.add_argument('--logtz', type = str, default='Europe/Berlin',
                        help = "TZ of times to convert to UTC")

    args = parser.parse_args()
    
    return Script_Arguments(
        args.logdayformat,
        args.logprefix,
        args.logdir,
        args.logtz
    )

""" Get the list of logs"""
async def get_logs(
        logdayformat: str,
        logprefix: str,
        logdir: str) -> List:

    """ Get the list of logdays """
    logdays = (await get_logdays(
        logprefix, logdir, logdayformat
    ))

    logtasks = [asyncio.create_task(
        get_columns_from_csv(
            ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(*logtasks)

    return pd.DataFrame(index = logdays, data = logcolumns)


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    """ Get the dictionary with all the power recordings per logdays """
    logsdf = await get_logs(
        args.logdayformat,
        args.logprefix,
        args.logdir
    )

    logdays = logsdf.index.values
    logger.info(f'Have {len(logdays)} logs')
    
    dfs = [pd.DataFrame(
        data = dict(logsdf.loc[ld, :]),
    ) for ld in logdays]

    for df in dfs:
        ##print(pd.to_datetime(df['TIME']).dt.tz_localize(args.logtz, ambiguous='infer')) #.dt.tz_convert('utc'))
        df['TIME'] = pd.to_datetime(df['TIME']) \
                       .dt.tz_localize(args.logtz, ambiguous= False) \
                          .dt.tz_convert('utc') \
                             .dt.tz_localize(None)

        
    dfs[-1].to_csv('zz.out', index=False)
    #print(pd.to_datetime(basedfs[0].TIME).tz_localize('utc'))
    #print(logsdf.iloc[0].loc['TIME',:])  ## .index.tz_localize('utc').tz_convert(args.tz))
            
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    logger.info(f'solar_checker_convert begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_convert end (err={err})')
    sys.exit(err)
