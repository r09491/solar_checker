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
    List, Optional
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
) -> List:
    
    days = await get_logdays(
        logprefix = args.logprefix,
        logdir = args.logdir
    )
    if days is None:
        logger.error("Failed to get logdays")
        return None

    yesterday, today = days[-2:]
    logger.info(f'Predicting "{today}" using "{yesterday}"')

    yesterday, todaylog = await asyncio.gather(
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
    yesterday.index = pd.date_range(
        todaylog.index[0].date(),
        periods=24,
        freq="h"
    )

    # Keep SOC
    realsoc = todaylog["SBSB"].iloc[0]
    
    # Calc prediction data
    realstop = yesterday.index[len(todaylog.index)-1]
    caststart = yesterday.index[len(todaylog.index)]
    reallast = todaylog.loc[realstop ,"SBPI"]
    castlast = yesterday.loc[realstop ,"SBPI"]
    adaptratio = reallast/castlast if castlast >0.0 else 0.0

    logger.info(f'Last real stop is "{realstop}"')
    logger.info(f'Last real irridiance is "{reallast}"')
    logger.info(f'Last cast irridiance is "{castlast}"')
    logger.info(f'Last real/cast ratio is "{adaptratio}"')

    # The restlog needs adaptation
    restlog = yesterday.loc[caststart:,:]
    if adaptratio >0.0:
        """ Try the cast with latest ratio """
        # Cast irridiance by scalling using last hour
        restlog["SBPI"] *= adaptratio

        # Simultate low irradiance
        issbpi = restlog["SBPI"] <35 
        restlog.loc[issbpi, "SBPB"] = -restlog.loc[issbpi, "SBPI"]
        restlog.loc[issbpi, "SBPO"] = 0

        # Simultate grey irradiance
        issbpi = (restlog["SBPI"] >=35) & (restlog["SBPI"] <100)
        restlog.loc[issbpi,"SBPB"] = 0
        restlog.loc[issbpi,"SBPO"] = restlog.loc[issbpi, "SBPI"]

        # Simultate bright irradiance
        issbpi = (restlog["SBPI"] >=100) & (restlog["SBPI"] <800)
        restlog.loc[issbpi,"SBPB"] = -restlog.loc[issbpi,"SBPI"] + 100
        restlog.loc[issbpi,"SBPO"] = 100

        # Simultate high irradiance
        issbpi = (restlog["SBPI"] >=800)
        restlog.loc[issbpi,"SBPB"] = -600
        restlog.loc[issbpi,"SBPO"] =  restlog.loc[issbpi,"SBPI"] - 600

    #Best cast is real data
    castlog = pd.concat([todaylog,restlog])

    # Simulate battery full
    isfull = castlog["SBPB"].cumsum() <-1600
    castlog.loc[isfull,"SBPB"] = 0
    castlog.loc[isfull,"SBPO"] = castlog.loc[isfull, "SBPI"]

    # Simulate battery empty
    isempty = castlog["SBPB"].cumsum() >0
    castlog.loc[isempty,"SBPB"] = 0
    castlog.loc[isempty,"SBPO"] = 0
    
    castlog["SBSB"] = realsoc - castlog["SBPB"].cumsum()/1600

    return castlog, caststart


""" 
Print the prediction data frames. 
"""
async def output_hour(
        predicttable: pd.DataFrame,
        caststart: pd.Timestamp
) -> None:
    
    pd.options.display.float_format = '{:,.1f}'.format

    w = predicttable[predicttable.columns[:-1]]
    print(f"\nRelative Watts @ {caststart}")
    print(w)

    print(f"\nAbsolute Watts @ {caststart}")
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

        w, caststart = await predict_hour(args)
        if w is None:
            logger.error(f'Hour Predict failed')
            return -1

        await output_hour(w, caststart)
        
        return 0

        
    try:
        err = asyncio.run(main(parse_arguments()))
    except KeyboardInterrupt: 
        err = 99
       
    sys.exit(err)
