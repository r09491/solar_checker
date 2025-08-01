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

import os
import sys
import asyncio

import pandas as pd
import numpy as np

from functools import reduce

from datetime import (
    datetime,
    timedelta
)

from .typing import (
    f64, t64, Any, Optional, List, Dict
    )
from .common import (
    t64_first,
    t64_last,
    t64_to_hm,
    t64_from_iso,
    t64_h_next,
    t64_h_first,
    t64_h_last,
    ymd_tomorrow,
    ymd_yesterday,
    ymd_over_t64
    )
from .common import (
    PARTITION_NAMES
)
from .samples import(
    get_columns_from_csv,
)
from .csvlog import(
    get_logdays
)

""" Get the list of logdays and the list of dictionaries with all the
recordings """
async def get_logs_as_lists(
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str) -> List:

    """ Get the list of logdays """
    logdays = (await get_logdays(
        logprefix, logdir, logdayformat
    ))[-logmaxdays:]

    logtasks = [asyncio.create_task(
        get_columns_from_csv(
            ld, logprefix, logdir
        )) for ld in logdays]
    
    """ Get the list of associated columns """
    logcolumns = await asyncio.gather(*logtasks)
    
    return logdays, logcolumns


""" Get the dataframe with the list of logdays and the list of
dictionaries with all the recordings """
async def get_logs_as_dataframe(
        logcols: List,
        logmaxdays: int,
        logdayformat: str,
        logprefix: str,
        logdir: str) -> pd.DataFrame:
    
    logdays, logcolumns = await get_logs_as_lists(
        logmaxdays, logdayformat, logprefix, logdir
    )
    
    return pd.DataFrame(index = logdays, data=logcolumns)[logcols]


""" Get the start and stop of the evaluation slot """
def get_on_times(log: list) -> Optional[List[t64]]:
    ison = log.iloc[-1]>0 # The data of the log day are at the very end
    if ~ison.any(): # no radiation
        return None, None
    time = log['TIME'] # Ensure time is always present!
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
        logsdf: pd.DataFrame,
        logday: str,
        starttime: t64,
        stoptime: t64,
        columns: str) -> list:

    """ Get the requested input columns """
    incols = ('TIME,' + columns).split(',')

    """ Extract the vector with log days """
    logdays = list(logsdf.index.values.tolist())

    
    """ All basic input cols without extensions """
    basecols = list(set([c for c in [cc[:-1]
                    if cc[-1] in "+-"
                    else cc for cc in incols[1:]]]))

    """ Samples for all log days in full time range synced to the minute """
    basedfs = [pd.DataFrame(
        index = logsdf.loc[ld, 'TIME'],
        data = dict(logsdf.loc[ld, basecols])
    ) for ld in logdays]

    
    """ Get the start and stop of the radiation. The times are
    determined from the first input power column after TIME """

    startontime, stopontime = get_on_times(
        logsdf.loc[logday, ['TIME', 'SBPI']]
    )

    if startontime is None or  stopontime is None:
        return None, None, None 

    starttime = startontime if starttime is None else \
        max(ymd_over_t64(starttime,logday), startontime)
    stoptime = stopontime if stoptime is None else \
        min(ymd_over_t64(stoptime,logday), stopontime)

    
    """ All basic samples for all log days for the requested time
    slot. Skip time solt if samples are missing. """
    
    slotdfs = []
    slotdays = []
    for (ld, bdf) in zip(logdays, basedfs):
        try:
            slot = bdf.loc[ymd_over_t64(starttime,ld):
                           ymd_over_t64(stoptime,ld),:]
        except KeyError:
            logger.warning(f'Samples of "{ld}" between "{starttime}" and "{stoptime}" missing. Skip!')
            continue
        slotdfs.append(slot)
        slotdays.append(ld)
    
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

    """ Create the energy (Wh) dataframe for all logdays """

    """
    wattsdf = pd.concat(
        [pd.DataFrame({'LOGDAY':slotdays}),
         pd.DataFrame([edf.sum()/60 for edf in eslotdfs])], axis=1
    )
    """
    wattsdf = pd.concat(
        [pd.DataFrame({'LOGDAY':slotdays}),
         pd.DataFrame([edf.mean()/edf.std() for edf in eslotdfs])], axis=1
    )  

    """ Use logday as index """
    wattsdf.set_index('LOGDAY', inplace = True)

    """ Remove apriori impossible list entries """
    watts = [wattsdf[d] for d in wattsdf.loc[:,incols[2:]]]
    wattsdrops = [list(w[~((w<0)|(w>0))
                         if (w.iloc[slotdays.index(logday)]<0 or
                             w.iloc[slotdays.index(logday)]>0)
                         else ((w<0)|(w>0))]
                       .index.values)
                  for w in watts]
    flatdrops = [alldrops for drops in wattsdrops
                 for alldrops in drops]
    wattsdf.drop(flatdrops, inplace = True)

        
    """ Calculate the norm vector from the watts (=>1). The
    'TIME'column (0) is not considered! """
    closeness = (wattsdf.loc[:,incols[1]] -
                 wattsdf.loc[logday, incols[1]])**2 # after TIME
    for c in incols[2:]:
        closeness += (wattsdf.loc[:,c] - wattsdf.loc[logday, c])**2
    wattsdf['CLOSENESS'] = np.sqrt(closeness)

    wattsdf.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )

    return starttime, stoptime, wattsdf


""" 
Get the partitoned prediction dictionary. The first day in the closest
days list is the day to be predicted. The successors are used for
prediction
"""
async def partition_closest_watts(
        logsdf: pd.DataFrame,
        starttime: t64,
        stoptime: t64,
        closestdays: List) -> Any:

    # Available days with logs
    logsdays = list(logsdf.index.values)
    
    # The days of interest
    doi = list(closestdays.index.values)

    # The day for prediction
    today = doi[0]
    # The closest days used for prediction
    todaydays = doi[1:]

    # The day for prediction
    tomorrow = ymd_tomorrow(today)
    # The closest days used for prediction
    tomorrowdays = [ymd_tomorrow(td)
                    for td in todaydays
                    if ((ymd_tomorrow(td) in logsdays)
                        and (ymd_tomorrow(td) != today))]

    
    # Time of the first and last sample
    logstarttime = logsdf.loc[today, 'TIME'][0]
    logstoptime = logsdf.loc[today, 'TIME'][-1]

    
    """ The data already recorded without partitioning """
    realseries = logsdf.loc[today]
    realdf = pd.DataFrame(index = realseries.iloc[0],
                           data = dict(realseries.iloc[1:]))
    realsoc = realdf.loc[:, 'SBSB'].iloc[-1]

    
    """ The frame with the watts before searching. Can be empty! """
    prewatts = realdf.loc[logstarttime:starttime,:].iloc[:-1]

    """ The frame with the watts in the search slot. Never empty! """
    findwatts = realdf.loc[starttime:stoptime,:]

    """ The frame with the watts after the search slot. Can be empty! """
    postwatts = realdf.loc[stoptime:logstoptime,:].iloc[1:]
    
    """ The predicted data for the day until time of last sample """    
    todaydfs = [
        pd.DataFrame(
            index = [ymd_over_t64(t, today) for t in ps.iloc[0]], 
            data = dict(ps[1:])
        ) for ps in [logsdf.loc[pd] for pd in todaydays]]

    todaywatts = (reduce(
        lambda x,y: x+y,
        [pdf.loc[logstoptime:,:] for pdf in todaydfs]
    ) / len(todaydfs))[1:]

    
    """ The tomorrow data for the day from midnight """    

    tomorrowdfs = [
        pd.DataFrame(
            index = [ymd_over_t64(
                t, tomorrow
            ) for t in ts.iloc[0]],
            data = dict(ts[1:])
        ) for ts in [logsdf.loc[td] for td in tomorrowdays]]

    # Arittmetic middle of days
    tomorrowwatts = (reduce(
        lambda x,y: x+y,
        [tdf for tdf in tomorrowdfs]
    ) / len(tomorrowdfs)) if len(tomorrowdfs)>0 else None 

    try:
        tomorrowwatts1 = (tomorrowwatts.loc[
            :ymd_over_t64(starttime, tomorrow)
        ][:-1]) if tomorrowwatts is not None else None
    except KeyError:
        tomorrowwatts1 = None

    try:
        tomorrowwatts2 = (tomorrowwatts.loc[
            ymd_over_t64(starttime, tomorrow):
        ].copy()) if tomorrowwatts is not None else None
    except KeyError:
        tomorrowwatts2  =None

    
    return ([today] + todaydays,
            [tomorrow] + tomorrowdays, realsoc,
            dict({'prewatts' : prewatts,
                  'findwatts' : findwatts,
                  'postwatts' : postwatts,
                  'todaywatts' : todaywatts,
                  'tomorrowwatts1' : tomorrowwatts1,
                  'tomorrowwatts2' : tomorrowwatts2}))


""" Assemble the prediction data frames for today  """
def concat_today(partitions: dict) -> pd.DataFrame:
    return pd.concat([partitions['prewatts'],
                      partitions['findwatts'],
                      partitions['postwatts'],
                      partitions['todaywatts']], sort = False)
    
""" Assemble the prediction data frames for tomorrow  """
def concat_tomorrow(partitions: dict) -> pd.DataFrame:
    return pd.concat([partitions['tomorrowwatts1'],
                      partitions['tomorrowwatts2']], sort = False)

""" Assemble the prediction data frames for tomorrow  """
def concat_total(partitions: dict) -> pd.DataFrame:
    return pd.concat([partitions['prewatts'],
                      partitions['findwatts'],
                      partitions['postwatts'],
                      partitions['todaywatts'],
                      partitions['tomorrowwatts1'],
                      partitions['tomorrowwatts2']], sort = False)

def get_predict_table(partitions: dict) -> pd.DataFrame:

    for watts in partitions.values():
        if (watts is None) or (watts.size == 0):
            continue

        watts.loc[:, 'SBPB-'] = watts.loc[:, 'SBPB']
        discharging = watts.loc[:, 'SBPB']>0
        watts.loc[discharging, 'SBPB-'] = 0

        watts.loc[:, 'SBPB+'] = watts.loc[:, 'SBPB']
        charging = watts.loc[:, 'SBPB']<0
        watts.loc[charging, 'SBPB+'] = 0

        watts.loc[:, 'SMP-'] = watts.loc[:, 'SMP']
        importing = watts.loc[:, 'SMP']>0
        watts.loc[importing, 'SMP-'] = 0
        
        watts.loc[:, 'SMP+'] = watts.loc[:, 'SMP']
        exporting = watts.loc[:, 'SMP']<0
        watts.loc[exporting, 'SMP+'] = 0

    phase = [k for (k,v) in partitions.items() if (
        (v is not None) and (len(v) >0)
    )]
    start = [t64_to_hm(v.index.values[0]) for (k,v) in partitions.items() if (
        (v is not None) and (v.size >0)
    )]
    stop = [t64_to_hm(v.index.values[-1]) for (k,v) in partitions.items() if (
        (v is not None) and (v.size >0)
    )]
    swatts = pd.concat([v.sum()/60 for (k,v) in partitions.items() if (
        (v is not None) and (v.size >0)
    )], axis=1)
        
    swattphases = pd.concat(
        [pd.DataFrame(
            {'PHASE':phase,
             'START': start,
             'STOP': stop}), swatts.T
        ], sort=False, axis=1)
    swattphases.set_index('PHASE', inplace=True)


    startstop = swattphases.loc[:, ['START', 'STOP']]
    watts = swattphases.loc[:, PARTITION_NAMES]
    relative_watts = pd.concat([startstop, watts], axis=1)


    bat_soc_start =  0 if partitions['prewatts'].empty else partitions['prewatts'].iloc[0,:]['SBPB-']
        
    return relative_watts, bat_soc_start # percent
