__doc__=""" Output hourly cast results
"""
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import pandas as pd
pd.options.display.float_format = '{:,.0f}'.format

from utils.common import(
    PARTITION_2_VIEW
)

async def get_hourly_cast_watts(
        pool: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):

    if pool is None:
        print(f'No cast available')
        return None, None

    pool.set_index('TIME', inplace=True)
    
    #means = pool.resample('h').mean() 

    sbpi_pool = pool.loc[:,'SBPI']
    sbpb_pool = pool.loc[:,'SBPB']
    sbpo_pool = pool.loc[:,'SBPO']
    smp_pool = pool.loc[:,'SMP']

    sbpb_pool_in = sbpb_pool.copy() 
    sbpb_pool_in[sbpb_pool>0] = 0
    sbpb_pool_out = sbpb_pool.copy() 
    sbpb_pool_out[sbpb_pool<0] = 0
    
    smp_pool_in = smp_pool.copy() 
    smp_pool_in[smp_pool<0] = 0
    smp_pool_out = smp_pool.copy() 
    smp_pool_out[smp_pool>0] = 0

    sbsb_pool =  pool.loc[:,'SBSB']
    
    sample = pd.DataFrame(
        data = {
            "SBPI":sbpi_pool,
            "SBPO":sbpo_pool,
            ">SMP":smp_pool_out,
            "SMP>":smp_pool_in,
            ">SBPB":sbpb_pool_in,
            "SBPB>":sbpb_pool_out
        }
    )

    sbsb_df =pd.DataFrame({"BAT%":sbsb_pool})
    
    starts = sample.index.strftime("%H:00")
    stops = sample.index.strftime("%H:59")
    start_stop_df =pd.DataFrame({"START":starts, "STOP":stops})

    sbsb_df.reset_index(inplace = True, drop=True)
    sample.reset_index(inplace = True, drop=True)
    
    return start_stop_df, sample, sbsb_df


async def get_predict_tables(
        pool: pd.DataFrame,
        bat_full_wh: float = 1600
) -> (pd.DataFrame, pd.DataFrame):

    (start_stop_df, sample_df, sbsb_df) = await get_hourly_cast_watts(pool)
    if ((start_stop_df is None) or
        (sample_df is None)
    ): 
        logger.error(f'Cannot print hourly pool data')
        return None

    sample_df.rename(columns=PARTITION_2_VIEW, inplace=True)
        
    watts_table = pd.concat([start_stop_df, sample_df], axis=1)

    energy_table = pd.concat([start_stop_df, sample_df.cumsum(), sbsb_df], axis=1)
    energy_table['>BAT'] -= sbsb_df['BAT%'].iloc[0] / 100 * bat_full_wh
    
    return (watts_table, energy_table)
