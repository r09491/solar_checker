__doc__="""
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

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

from .types import (
    t64, Any, Optional, List, Dict
    )
from .common import (
    t64_first,
    t64_last,
    t64_to_hm,
    ymd_tomorrow,
    ymd_yesterday,
    ymd_over_t64
    )
from .samples import (
    get_columns_from_csv,
    get_logdays
    )

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(__file__))


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
    ison = log[-1]>0 # The data of the log day are at the very end
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

    
    """ All basic input cols without extension """
    basecols = set([c for c in [cc[:-1]
                    if cc[-1] in "+-"
                    else cc for cc in incols[1:]]])

    """ All basic samples for all log days in the full time range """
    basedfs = [pd.DataFrame(
        index = logsdf.loc[ld, 'TIME'],
        data = dict(logsdf.loc[ld, basecols])
    ) for ld in logdays]

    
    """ Get the start and stop of the radiation. The times are
    determined from the first input power column after TIME """

    startontime, stopontime = get_on_times(
        logsdf.loc[logday, [incols[0],
                            incols[1][:-1]
                            if incols[1][-1] == '+' else
                            incols[1]]] # TIME and first column
    )

    if startontime is None or  stopontime is None:
        return None, None, None 

    starttime = startontime if starttime is None else \
        max(ymd_over_t64(starttime,logday), startontime)
    stoptime = stopontime if stoptime is None else \
        min(ymd_over_t64(stoptime,logday), stopontime)

    starttime = t64_first(starttime)
    stoptime = t64_last(stoptime)

    """ All basic samples for all log days for the requested time slot """
    slotdfs = [bdf.loc[ymd_over_t64(starttime,ld):
                       ymd_over_t64(stoptime,ld),:]
               for ld, bdf in zip (logdays, basedfs)]

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

    wattsdf = pd.concat(
        [pd.DataFrame({'LOGDAY':logdays}),
         pd.DataFrame([edf.sum()/60 for edf in eslotdfs])], axis=1
    )

    """ Use logday as index """
    wattsdf.set_index('LOGDAY', inplace = True)

    """ Remove apriori impossible list entries """
    watts = [wattsdf[d] for d in wattsdf.loc[:,incols[2:]]]
    wattsdrops = [list(w[~((w<0)|(w>0))
                         if (w[logdays.index(logday)]<0 or
                             w[logdays.index(logday)]>0)
                         else ((w<0)|(w>0))]
                       .index.values)
                  for w in watts]
    flatdrops = [alldrops for drops in wattsdrops for alldrops in drops]
    wattsdf.drop(flatdrops, inplace = True)

        
    """ Calculate the norm vector from the watts """
    closeness = (wattsdf[incols[1]] -
                 wattsdf.loc[logday, incols[1]])**2 # after TIME
    for c in incols[2:]:
        closeness += (wattsdf[c] - wattsdf.loc[logday, c])**2
    wattsdf['CLOSENESS'] = np.sqrt(closeness)

    wattsdf.sort_values(by = 'CLOSENESS', ascending = True, inplace = True )

    return starttime, stoptime, wattsdf


""" 
Get the prediction dictionary. The first day in the closest days
list is the day to be predicted. The followers are used for prediction 
"""
async def predict_closest(
        logsdf: pd.DataFrame,
        starttime: t64,
        stoptime: t64,
        closestdays: List) -> Any:

    # The days of interest
    doi = list(closestdays.index.values)

    # The day for prediction
    today = doi[0]

    # The closest days used for prediction
    predictdays = doi[1:]

    # The days after the closest days
    tomorrowdays = [ymd_tomorrow(pd)
                    for  pd in predictdays
                    if pd != ymd_yesterday(today)]

    # Time of the first and last sample
    logstarttime = logsdf.loc[today, 'TIME'][0]
    logstoptime = logsdf.loc[today, 'TIME'][-1]

    """ The data already recorded """
    todayseries = logsdf.loc[today]
    todaydf = pd.DataFrame(index = todayseries[0],
                           data = dict(todayseries[1:]))

    """ The frame with the watts before teh watts use for searching  """
    prewatts = todaydf.loc[logstarttime:starttime,:]


    """ The frame with the watts in the search slot  """
    findwatts = todaydf.loc[starttime:stoptime,:]


    """ The frame with the watts after the search slot  """
    postwatts = todaydf.loc[stoptime:logstoptime,:]

    """ The predicted data for the day until time of last sample """    
    predictdfs = [
        pd.DataFrame(
            index = [ymd_over_t64(t, today) for t in ps[0]], 
            data = dict(ps[1:])
        ) for ps in [logsdf.loc[pd] for pd in predictdays]]

    predictwatts = reduce(
        lambda x,y: x+y,
        [pdf.loc[logstoptime:,:] for pdf in predictdfs]
    ) / len(predictdfs)

    #Plausibility

    sbpi = predictwatts.SBPI
    sbpb = predictwatts.SBPB
    sbpo = predictwatts.SBPO
    haveenergy = (sbpi>0) | (sbpb>0)
    clearsbpo = ~haveenergy & (sbpo>0)
    predictwatts.SBPO[clearsbpo] = 0

    sbpo = predictwatts.SBPO
    haveoutput = sbpo>0
    ivp1 = predictwatts.IVP1
    predictwatts.IVP1[~haveoutput & (ivp1>0)] = 0
    ivp2 = predictwatts.IVP2
    predictwatts.IVP2[~haveoutput & (ivp2>0)] = 0
    spph = predictwatts.SPPH
    predictwatts.SPPH[~haveoutput & (spph>0)] = 0
    
    smp = predictwatts.SMP
    smp = predictwatts.SMP
    sbpb = predictwatts.SBPB
    adaptsmp = (sbpb>0) & (smp>0)
    predictwatts.SBPB[adaptsmp] = sbpb+smp
    predictwatts.SMP[adaptsmp] = 0

    sbpb = predictwatts.SBPB
    ivp = predictwatts.IVP1+predictwatts.IVP2
    sbpo = predictwatts.SBPO
    replacesbpb = (sbpb>0) & ((sbpo<=0)|(ivp<=0)) & (smp<=0)
    predictwatts.SMP[replacesbpb] = sbpb
    predictwatts.SBPB[replacesbpb] = 0

    sbpb = predictwatts.SBPB
    ivp = predictwatts.IVP1+predictwatts.IVP2
    sbpbivp_higher = (sbpb>0) & (sbpb>ivp)
    predictwatts.SBPB[sbpbivp_higher] = ivp[sbpbivp_higher] 

    sbpi = predictwatts.SBPI
    sbpb = predictwatts.SBPB
    clearsbpb = (sbpi>0) & (sbpb>0)
    predictwatts.SBPB[clearsbpb] = 0
    
    
    """ The tomorrow data for the day from midnight """    
    tomorrowdfs = [
        pd.DataFrame(
            index = [ymd_over_t64(
                t, ymd_tomorrow(today)
            ) for t in ts[0]],
            data = dict(ts[1:])
        ) for ts in [logsdf.loc[td] for td in tomorrowdays]]

    # Arittmetic middle of days
    tomorrowwatts = reduce(
        lambda x,y: x+y,
        [tdf for tdf in tomorrowdfs]
    ) / len(tomorrowdfs)
   
    #Plausibility

    sbpi = tomorrowwatts.SBPI
    sbpb = tomorrowwatts.SBPB
    sbpo = tomorrowwatts.SBPO
    haveenergy = (sbpi>0) | (sbpb>0)
    clearsbpo = ~haveenergy & (sbpo>0)
    tomorrowwatts.SBPO[clearsbpo] = 0

    sbpo = tomorrowwatts.SBPO
    ivp1 = tomorrowwatts.IVP1
    haveoutput = sbpo>0
    tomorrowwatts.IVP1[~haveoutput & (ivp1>0)] = 0
    ivp2 = tomorrowwatts.IVP2
    tomorrowwatts.IVP2[~haveoutput & (ivp2>0)] = 0
    spph = tomorrowwatts.SPPH
    tomorrowwatts.SPPH[~haveoutput & (spph>0)] = 0
    
    smp = tomorrowwatts.SMP
    sbpb = tomorrowwatts.SBPB
    adaptsmp = (sbpb>0) & (smp>0)
    tomorrowwatts.SBPB[adaptsmp] = sbpb+smp
    tomorrowwatts.SMP[adaptsmp] = 0

    smp = tomorrowwatts.SMP
    sbpb = tomorrowwatts.SBPB
    ivp = tomorrowwatts.IVP1+tomorrowwatts.IVP2
    sbpo = tomorrowwatts.SBPO
    replacesbpb = (sbpb>0) & ((sbpo<=0)|(ivp<=0)) & (smp <=0)
    tomorrowwatts.SMP[replacesbpb] = sbpb
    tomorrowwatts.SBPB[replacesbpb] = 0
    
    sbpb = tomorrowwatts.SBPB
    ivp = tomorrowwatts.IVP1+tomorrowwatts.IVP2
    sbpbivp_higher = (sbpb>0) & (sbpb>ivp)
    tomorrowwatts.SBPB[sbpbivp_higher] = ivp[sbpbivp_higher] 

    sbpi = tomorrowwatts.SBPI
    sbpb = tomorrowwatts.SBPB
    clearsbpb = (sbpi>0) & (sbpb>0)
    tomorrowwatts.SBPB[clearsbpb] = 0

    tomorrowwatts1 = tomorrowwatts.loc[
        :ymd_over_t64(starttime, ymd_tomorrow(today))
    ][:-1]
    
    tomorrowwatts2 = tomorrowwatts.loc[
        ymd_over_t64(starttime, ymd_tomorrow(today)):
    ]
    
    return prewatts, findwatts, postwatts, predictwatts, tomorrowwatts1, tomorrowwatts2


""" Assemble the prediction data frames for today  """
def concat_predict_today(
        findwatts: pd.DataFrame,
        postwatts: pd.DataFrame,
        predictwatts: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([findwatts,
                      postwatts,
                      predictwatts])

""" Assemble the prediction data frames for tomorrow  """
def concat_predict_tomorrow1(
        findwatts: pd.DataFrame,
        postwatts: pd.DataFrame,
        predictwatts: pd.DataFrame,
        tomorrowwatts1: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([findwatts,
                      postwatts,
                      predictwatts,
                      tomorrowwatts1])

""" Assemble the prediction data frames for tomorrow  """
def concat_predict_tomorrow2(
        findwatts: pd.DataFrame,
        postwatts: pd.DataFrame,
        predictwatts: pd.DataFrame,
        tomorrowwatts1: pd.DataFrame,
        tomorrowwatts2: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([findwatts,
                      postwatts,
                      predictwatts,
                      tomorrowwatts1,
                      tomorrowwatts2])


def get_predict_table(
        prewatts: pd.DataFrame,
        findwatts: pd.DataFrame,
        postwatts: pd.DataFrame,
        predictwatts: pd.DataFrame,
        tomorrowwatts1: pd.DataFrame,
        tomorrowwatts2: pd.DataFrame) -> pd.DataFrame:
    
    input = vars()

    for watts in input.values():
        if watts.size == 0:
            continue
        watts['SBPB-'] = watts['SBPB'][(watts['SBPB']<0)]
        watts['SBPB+'] = watts['SBPB'][(watts['SBPB']>0)]
        watts['SMP+'] = watts['SMP'][(watts['SMP']>0)]
        watts['SMP-'] = watts['SMP'][(watts['SMP']<0)]
        watts['IVP'] = watts['IVP1'] + watts['IVP2']
        #watts.drop(['SBPB','SMP','IVP1','IVP2'], inplace=True, axis=1)
                
    
    phase = [k for (k,v) in input.items() if len(v) >0]
    start = [t64_to_hm(v.index.values[0]) for (k,v) in input.items() if v.size >0]
    stop = [t64_to_hm(v.index.values[-1]) for (k,v) in input.items() if v.size >0]
    swatts = pd.concat([v.sum()/60 for (k,v) in input.items() if (v.size >0)], axis=1)
        
    swattphases = pd.concat(
        [pd.DataFrame(
            {'PHASE':phase,
             'START': start,
             'STOP': stop}), swatts.T
        ], sort=False, axis=1)
    swattphases.set_index('PHASE', inplace=True)


    startstop = swattphases.loc[:, ['START', 'STOP']]
    watts = swattphases.loc[:,['SBPI','SBPB-','SBPB+','SBPO','IVP','SMP-','SMP+']]
    ##smp = swattphases.loc[:,['SMP+', 'SMP-']]
    relative_watts = pd.concat([startstop, watts], axis=1)

    bat_soc_start =  prewatts.iloc[0,:]['SBPB-']
    
    return relative_watts, bat_soc_start # percent
