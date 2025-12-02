#!/usr/bin/env python3

__doc__="""
Writes a prediction table for the rest of today estimating the irridance and using a solarbank model dependent on the irridiance.
"""

__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

import numpy as np
import pandas as pd

from dataclasses import dataclass

from utils.typing import(
    Optional
)
from utils.common import(
    PREDICT_POWER_NAMES
)

from utils.csvlog import(
    get_logdays,
    get_log
)


LOGDIR='/home/r09491/storage/solar_checker'
LOGPREFIX='solar_checker_latest'

async def get_hour_log(
        logday: str,
        logprefix: str,
        logdir: str
):
    log = await get_log(
        logday = logday,
        logprefix = logprefix,
        logdir = logdir,
        usecols = PREDICT_POWER_NAMES
    )

    return log.set_index('TIME').resample('h').mean()


@dataclass
class Script_Arguments:
    logprefix: str
    logdir: str


async def predict_hour(
        args: Script_Arguments
) -> Optional[pd.DataFrame]:
    
    days = await get_logdays(
        logprefix = args.logprefix,
        logdir = args.logdir
    )
    if days is None:
        logger.error("Failed to get logdays")
        return None

    yesterday, today = days[-2:]
    logger.info(f'Predicting "{today}" using "{yesterday}"')

    
    castlog, todaylog = await asyncio.gather(
        get_hour_log(
            logday = yesterday,
            logprefix = args.logprefix,
            logdir = args.logdir
        ),
        get_hour_log(
            logday = today,
            logprefix = args.logprefix,
            logdir = args.logdir
        )
    )

    # Adapt the cast indices
    castlog.index = pd.date_range(
        todaylog.index[0].date(),
        periods=24,
        freq="h"
    )

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[0]
    
    # Calc prediction data
    realstop = castlog.index[len(todaylog.index)-1]
    caststart = castlog.index[len(todaylog.index)]
    reallast = todaylog.loc[realstop ,"SBPI"]
    castlast = castlog.loc[realstop ,"SBPI"]
    adaptratio = reallast/castlast if castlast >0.0 else 0.0

    logger.info(f'Current cast ratio is "{adaptratio}"')
    
    # Cast irridiance by scalling using last hour
    castlog["SBPI"] *= adaptratio


    # Simultate low irradiance
    issbpi = castlog["SBPI"] <35 
    castlog.loc[issbpi, "SBPB"] = castlog.loc[issbpi, "SBPI"]
    castlog.loc[issbpi, "SBPO"] = 0

    # Simultate medium irradiance
    issbpi = (castlog["SBPI"] >=35) & (castlog["SBPI"] <100)
    castlog.loc[issbpi,"SBPB"] = 0
    castlog.loc[issbpi,"SBPO"] = castlog.loc[issbpi, "SBPI"]

    # Simultate medium irradiance
    issbpi = (castlog["SBPI"] >=100) & (castlog["SBPI"] <800)
    castlog.loc[issbpi,"SBPB"] = castlog.loc[issbpi,"SBPI"] - 100
    castlog.loc[issbpi,"SBPO"] = 100

    # Simultate high irradiance
    issbpi = (castlog["SBPI"] >=800)
    castlog.loc[issbpi,"SBPB"] = 600
    castlog.loc[issbpi,"SBPO"] =  castlog.loc[issbpi,"SBPI"] - 600
    
    #Best cast is real data
    castlog.loc[:realstop,:] = todaylog

    # Simulate battery full
    isfull = castlog["SBPB"].cumsum() <-1600
    castlog.loc[isfull,"SBPB"] = 0
    castlog.loc[isfull,"SBPO"] = castlog.loc[isfull, "SBPI"]

    # Simulate battery empty
    isempty = castlog["SBPB"].cumsum() >0
    castlog.loc[isempty,"SBPB"] = 0
    castlog.loc[isempty,"SBPO"] = 0
    

    castlog["SBSB"] = realsoc - castlog["SBPB"].cumsum()/1600

    return castlog


""" 
Print the prediction data frames. 
"""
async def output_hour(
        predicttable: pd.DataFrame
) -> None:
    
    pd.options.display.float_format = '{:,.1f}'.format

    w = predicttable[predicttable.columns[:-1]]
    print("\nRelative Watts")
    print(w)

    print("\nAbsolute Watts")
    wh =  w.cumsum()
    sbsb = predicttable["SBSB"]
    print(pd.concat([wh, sbsb], axis=1))
    
    print()


if __name__ == '__main__':
    def parse_arguments() -> Script_Arguments:
        """Parse command line arguments"""

        parser = argparse.ArgumentParser(
            prog=os.path.basename(sys.argv[0]),
            description='Get the latest weather forecast',
            epilog=__doc__)

        parser.add_argument('--version', action = 'version', version = __version__)

        parser.add_argument(
            '--logprefix', type=str, default=LOGPREFIX,
            help = "The prefix used in log file names")

        parser.add_argument(
            '--logdir', type=str, default=LOGDIR,
            help = "The directory the logfiles are stored")
       
        args = parser.parse_args()

        return Script_Arguments(
            args.logprefix,
            args.logdir)


    async def main(args: Script_Arguments) -> int:

        w = await predict_hour(args)
        if w is None:
            logger.error(f'Hour Predict failed')
            return -1

        await output_hour(w)
        
        return 0

        
    try:
        err = asyncio.run(main(parse_arguments()))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
