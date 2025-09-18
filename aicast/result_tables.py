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
    
    means = pool.resample('h').mean() 

    sbpi_means = means.loc[:,'SBPI']
    sbpb_means = means.loc[:,'SBPB']
    sbpo_means = means.loc[:,'SBPO']
    smp_means = means.loc[:,'SMP']

    sbpb_means_in = sbpb_means.copy() 
    sbpb_means_in[sbpb_means>0] = 0
    sbpb_means_out = sbpb_means.copy() 
    sbpb_means_out[sbpb_means<0] = 0
    
    smp_means_in = smp_means.copy() 
    smp_means_in[smp_means<0] = 0
    smp_means_out = smp_means.copy() 
    smp_means_out[smp_means>0] = 0

    sbsb_means =  means.loc[:,'SBSB']
    
    means_df = pd.DataFrame(
        data = {
            "SBPI":sbpi_means,
            ">SBPB":sbpb_means_in,
            "SBPB>":sbpb_means_out,
            "SBPO":sbpo_means,
            ">SMP":smp_means_out,
            "SMP>":smp_means_in,
        }
    )

    sbsb_df =pd.DataFrame({"BAT%":sbsb_means})
    
    starts = means_df.index.strftime("%H:00")
    stops = means_df.index.strftime("%H:59")
    start_stop_df =pd.DataFrame({"START":starts, "STOP":stops})

    sbsb_df.reset_index(inplace = True, drop=True)
    means_df.reset_index(inplace = True, drop=True)
    
    return start_stop_df, means_df, sbsb_df


async def get_predict_tables(
        pool: pd.DataFrame,
        bat_full_w: float = 1600
) -> (pd.DataFrame, pd.DataFrame):

    (start_stop_df, means_df, sbsb_df) = await get_hourly_cast_watts(pool)
    if ((start_stop_df is None) or
        (means_df is None)
    ): 
        logger.error(f'Cannot print hourly pool data')
        return None

    means_df.rename(columns=PARTITION_2_VIEW, inplace=True)
        
    watts_table = pd.concat([start_stop_df, means_df], axis=1)

    energy_table = pd.concat([start_stop_df, means_df.cumsum(), sbsb_df], axis=1)
    energy_table['>BAT'] -= sbsb_df['BAT%'].iloc[0] / 100 * bat_full_w
    
    return (watts_table, energy_table)
