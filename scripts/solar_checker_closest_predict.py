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
    ison = logdata[-1]>0 # The data of the log day are at the very end
    if ~ison.any(): # no radiation
        return None, None
    time = logdata['TIME'] # Ensure time is always present!
    timeon = time[ison]
    return timeon[0], timeon[-1]

""" 
Find the list of closest log days for the requested log day for the
specified time slot.

For each logday the norm of the sample vector in the sample space is
built. The closest log day is the one where the difference of to
specified logday is a minimum.
"""    
async def find_closest(
        logsdf: Any,
        logday: str,
        starttime: t64,
        stoptime: t64,
        columns: str) -> list:

    """ Get the requested columns """
    incols = ('TIME,' + columns).split(',')

    " Extrect the vector with log days"
    logdays = list(logsdf.index.values.tolist())

    
    """ Get the start and stop of the radiation """

    startontime, stopontime = get_on_times(
        logsdf.loc[logday, [incols[0],
                            incols[1][:-1]
                            if incols[1][-1] == '+' else
                            incols[1]]] # TIME and first column
    )

    """ Override under certain conditions """
    starttime = startontime if starttime is None else \
        hm2time("00:00") if startontime is None else \
        max(starttime, startontime)
    stoptime = stopontime if stoptime is None else \
        hm2time("00:00") if stopontime is None else \
        min(stoptime, stopontime)

    
    
    """ Extract the slot samples in watt """

    # All basic input cols without extension
    basecols = set([c for c in [cc[:-1]
                if cc[-1] in "+-" else
                    cc for cc in incols]])

    # All basic samples for all log days in the full time range
    basedfs = [pd.DataFrame(
        dict(logsdf.loc[ld, basecols])
    ) for ld in logdays]

    
    # All basic samples for all log days for the requested time slot
    slotdfs = []
    for bdf in basedfs:
        bdf.set_index('TIME', inplace=True)
        slotdfs.append(bdf.loc[starttime:stoptime,:])
        bdf.reset_index(inplace=True)

    # All samples including extensions for all log days and requested slot
    eslotdfs = []
    for sdf in slotdfs:
        inseries = [sdf[c[:-1] if c[-1] in '+-' else c] for c in incols[1:]]
        eslotdfs.append(pd.DataFrame(dict(zip(incols[1:], inseries))))

    plus = [c for c in incols[1:] if c[-1] in '+']
    minus = [c for c in incols[1:] if c[-1] in '-']
    for edf in eslotdfs:
        for p in plus:
            pcol = edf.loc[:, p]
            pcol[pcol<0] = 0
            edf.loc[:, p] = pcol
        for m in minus:
            mcol = edf.loc[:, m]
            mcol[mcol>0] = 0
            edf.loc[:, m] = mcol

    
    """ Create the energy (kWh) dataframe for all logdays """

    wattsdf = pd.concat(
        [pd.DataFrame({'LOGDAY':logdays}),
         pd.DataFrame([edf.sum()/60/1000 for edf in eslotdfs])], axis=1
    )
    
    """ Calculate the norm vector from the watts """
    norm = wattsdf[incols[1]]**2 # after TIME
    for c in incols[2:]:
        norm += wattsdf[c]**2
    wattsdf['NORM'] = np.sqrt(norm)
    
    """ Calculate the closeness vector from norm """
    norm = wattsdf['NORM']
    bnorm = norm[logdays.index(logday)]
    wattsdf['CLOSENESS'] = abs(norm - bnorm)
    
    """ Add the logdays which can be used as index """
    wattsdf.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )
    return starttime, stoptime, wattsdf


""" 
Get the prediction dictionary. The first day in the closest days
list is the day to be predicted. The followers are used for prediction 
"""
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
    
    


@dataclass
class Script_Arguments:
    logday: str
    logdayformat: str
    logprefix: str
    logdir: str
    starttime: t64
    stoptime: t64
    predict: bool
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
        '--predict', type=bool, default=False,
        help = "Disable/Enable prediction")

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
        args.predict,
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
        print(f'No radiation for the log day detected!')
        return 1
    
    print(closestdays.head(n=20))

    start = pd.to_datetime(str(starttime)).strftime("%H:%M")
    stop = pd.to_datetime(str(stoptime)).strftime("%H:%M")
    print(f'\nUsed samples from "{start}" to "{stop}"')

    if args.predict:
        predict = await assemble_predict(
            logsdf, starttime, stoptime, closestdays.head(n=4)
        )
    
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
            print(f'"{c}" is a wrong sample name')
            sys.exit(2)

    if args.columns.split(',')[0][-1] in ['-']:
            print(f'first column must not have extension')
            sys.exit(3)
            
    logger.info(f'solar_checker_closest_find begin')
    
    try:
        err = asyncio.run(main(args))
    except KeyboardInterrupt: 
        err = 99

    logger.info(f'solar_checker_closest_find end (err={err})')
    sys.exit(err)
