#!/usr/bin/env python3

__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import pandas as pd
import numpy as np

from datetime import datetime, timedelta

from dataclasses import dataclass

from utils.types import t64, t64s, timeslots, Any, Optional, List, Dict
from utils.samples import get_columns_from_csv
from utils.samples import get_logdays


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(sys.argv[0]))

POWER_NAMES = [
    'TIME',
    'SMP', 
    'IVP1',
    'IVP2',
    'SPPH',
    'SBPI', 'SBPO', 'SBPB',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]

"""
Only power samples may be used. For some sanmple it is possible to
split between positive and negative values.
"""
INPUT_NAMES = [
    'SMP', 'SMP+', 'SMP-', 
    'IVP1',
    'IVP2',
    'SPPH',
    'SBPI', 'SBPO', 'SBPB', 'SBPB+','SBPB-',
    'SPP1', 'SPP2', 'SPP3', 'SPP4'
]


def hm2time(hm: str) -> t64s:
    return t64(datetime.strptime(hm, "%H:%M"))


""" Get the list of logdays and the list of dictionaries with all the
recordings """
async def get_logs_as_lists(
        logdayformat: str,
        logprefix: str,
        logdir: str) -> list:
    
    """ Get the list of logdays """
    logdays = await get_logdays(
        logprefix, logdir, logdayformat)
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(
        *[get_columns_from_csv(ld, logprefix, logdir) for ld in logdays])
    
    return logdays, logcolumns


""" Get the dataframe with the list of logdays and the list of
dictionaries with all the recordings """
async def get_logs_as_dataframe(
        logcols: list,
        logdayformat: str,
        logprefix: str,
        logdir: str) -> list:
    
    logdays, logcolumns = await get_logs_as_lists(
        logdayformat, logprefix, logdir)

    return pd.DataFrame(index = logdays, data=logcolumns)[logcols]

""" Get the start and stop of the evaluation slot """
def get_on_times(logdata: list) -> Optional[List[t64]]:
    ison = logdata[-1]>0
    if ~ison.any(): # no radiation
        return None, None
    time = logdata['TIME'] # Ensure time is always present!
    timeon = time[ison]
    return timeon[0], timeon[-1]


""" Get the prediction dictionary. The first day in the closest days
list is the day to be predicted. The followers are used for prediction """
async def assemble_predict(
        logsdf: Any,
        starttime: t64,
        stoptime: t64,
        closestdays: list) -> Dict:

    """ The data already recorded """
    bday = closestdays.iloc[0]['LOGDAY']
    bdata = logsdf.loc[bday]
    bdict = dict(bdata)
    bdf = pd.DataFrame(bdict)
    bdf.set_index('TIME', inplace=True)
    bdf = bdf.loc[starttime:stoptime,:]

    """ The predicted day """

    pdays = closestdays.iloc[1:]['LOGDAY']
    pdata = [logsdf.loc[d] for d in pdays]
    pdict = [dict(d) for d in pdata]
    pdfs = [pd.DataFrame(d) for d in pdict]

    for pdf in pdfs:
        pdf.set_index('TIME', inplace=True)
        pdf = pdf.loc[stoptime:,:]

    """ Reduce """
            
    rdf = pdfs[0]
    for pdf in pdfs[1:]:
        rdf += pdf
    rdf /= len(pdfs)

    """ Assemble recorded and predicted """
    bdf.append(pdf)
    print(bdf.head(n=5))
    print(bdf.tail(n=5))
    
    #TODO Add morning hours similar to evening hours
    
    
    
    
async def find_closest(
        logsdf: Any,
        logday: str,
        starttime: t64,
        stoptime: t64,
        columns: str) -> list:

    """ Get the requested columns """
    logcols = ('TIME,' + columns).split(',')

    " Extrect the vector with log days"
    logdays = list(logsdf.index.values.tolist())

    """ Get the start and stop time of the radiation from time vector
    and first column """
    startontime, stopontime = get_on_times(
        logsdf.loc[logday, logcols[:2]] # TIME and first column
    )

    """ Override under certain conditions """
    starttime = startontime if starttime is None else \
        hm2time("00:00") if startontime is None else \
        max(starttime, startontime)
    stoptime = stopontime if stoptime is None else \
        hm2time("00:00") if stopontime is None else \
        min(stoptime, stopontime)

    
    """ Extract the slot samples in watt """

    slotcols = set(c for c in [cc[:-1]
                if cc[-1] in "+,-" else
                    cc for cc in logcols])

    coldfs = [pd.DataFrame(
        dict(logsdf.loc[ld, slotcols]))
        for ld in logdays]

    slotdfs = []
    for cdf in coldfs:
        cdf.set_index('TIME', inplace=True)
        slotdfs.append(cdf.loc[starttime:stoptime,:])

        
    """ Add the +/-extensions to the the log dataframe """

    srccols = (c[:-1] for c in logcols if c[-1] in "+,-" )
    dstcols = (c for c in logcols if c[-1] in "+,-" )

    for sdf in slotdfs:
        for d,s in zip(dstcols ,srccols):
            sdf[d] = sdf[s].copy()
            if d[-1] == '-':
                sdf[d][sdf[s]>0] = 0
            else:
                sdf[d][sdf[s]<0] = 0
        sdf.reset_index(inplace=True)

    wattsdf = pd.DataFrame([sdf.sum()/60 for sdf in slotdfs])
    
    """ Build the state vector from the watts """
    state = wattsdf[logcols[1]]**2 # after TIME
    for c in logcols[2:]:
        state += wattsdf[c]**2
    wattsdf['STATE'] = np.sqrt(state)
    
    """ Calculate the closeness vector from state """
    state = wattsdf['STATE']
    bstate = state[logdays.index(logday)]
    wattsdf['CLOSENESS'] = state - bstate
    
    """ Add the logdays which can be used as index """
    wattsdf['LOGDAY'] = logdays
    wattsdf.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )
    return starttime, stoptime, wattsdf


@dataclass
class Script_Arguments:
    logday: str
    logdayformat: str
    logprefix: str
    logdir: str
    starttime: t64
    stoptime: t64
    columns: str

def parse_arguments() -> Script_Arguments:
    description='Find a list of the closest log files for the given basefile'
    parser = argparse.ArgumentParser(description)

    parser.add_argument('--version', action = 'version',
                        version = __version__)

    parser.add_argument(
        '--logday', type=str,
        help = "Day to which to find the closest")

    parser.add_argument(
        '--logdayformat', type=str,
        help = "Days to which to find the closest")
    
    parser.add_argument(
        '--logprefix', type=str,
        help = "The prefix used in log file names")

    parser.add_argument(
        '--logdir', type=str,
        help = "The directory the logfiles are stored")
    
    parser.add_argument(
        '--starttime', type=hm2time, default=None,
        help = "The start time of the slot")

    parser.add_argument(
        '--stoptime', type=hm2time, default=None,
        help = "The end time of the slot")

    parser.add_argument(
        '--columns', type=str,
        help = "The list names of the to be used. The first determines the time slot for the evaluation an prediction"
    )

    args = parser.parse_args()
    
    return Script_Arguments(
        args.logday,
        args.logdayformat,
        args.logprefix,
        args.logdir,
        args.starttime,
        args.stoptime,
        args.columns,
    )


async def main( args: Script_Arguments) -> int:
    args = parse_arguments()

    """ Get the dictionary with all the power recordings per logdays """
    logsdf = await get_logs_as_dataframe(
        POWER_NAMES, args.logdayformat, args.logprefix, args.logdir
    )

    starttime, stoptime, closestdays = await find_closest(
        logsdf, args.logday, args.starttime, args.stoptime, args.columns
    )
    if (starttime is None or
        stoptime is None or
        closestdays is None):
        print(f'No radiation detected!')
        return 1
    
    print(closestdays.head(n=20))

    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")
    print(f'\nUsed samples from "{start}" to "{stop}"')

    """
    predict = await assemble_predict(
        logsdf, starttime, stoptime, closestdays.head(n=4)
    )
    """
    return 0


if __name__ == '__main__':
    args = parse_arguments()

    if (args.stoptime is not None and
        args.starttime is not None and
        args.stoptime <= args.starttime):
        logger.error(f'time slot is empty')
        sys.exit(1)

    for c in args.columns.split(','):
        if not c in INPUT_NAMES:
            logger.error(f'column is a wrong sample name')
            sys.exit(2)

    if args.columns.split(',')[0][-1] in ['+', '-']:
            logger.error(f'First column must not have extension')
            sys.exit(3)
            
    logger.info(f'solar_checker_closest_find begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
