from ..typing import (
    t64, t64s,
    f64, f64s, Any
)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches

import numpy as np

import base64
from io import BytesIO

from datetime import datetime


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)


XSIZE, YSIZE = 10, 5

def _get_w_line(time: t64s, smp: f64s,
                ivp1: f64s, ivp2: f64s, spph: f64s,
                sbpi: f64s, sbpo: f64s, sbpb: f64s,
                tphases: t64s = None):
    __me__ ='_get_w_line'
    logger.info(f'started')

    # ?Have data (smartmeter)
    smpon = np.zeros_like(smp)
    issmpon = smp>0 if smp is not None else None
    smpon[issmpon] = smp[issmpon] 
    smpon_mean = 0 if not issmpon.any() else smpon.mean()
    smpon_max = 0 if not issmpon.any() else smpon.max()

    smpoff = np.zeros_like(smp)
    issmpoff = smp<0 if smp is not None else None
    smpoff[issmpoff] = smp[issmpoff] 
    smpoff_mean = 0 if not issmpoff.any() else smpoff.mean()
    smpoff_min = 0 if not issmpoff.any() else smpoff.min()

    # ?Have data (inverter)
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp2 is not None else None 
    isivpon = ivp>0 if ivp is not None else None
    ivpon = ivp[isivpon] if isivpon is not None and isivpon.any() else None
    ivpon_mean = ivpon.mean() if ivpon is not None else 0
    ivpon_max = ivpon.max() if ivpon is not None else 0

    # ?Have power ( smartplug)
    isspphon = spph>0 if spph is not None else None
    spphon = spph[isspphon] if isspphon is not None and isspphon.any() else None
    spphon_mean = spphon.mean() if spphon is not None else 0
    spphon_max = spphon.max() if spphon is not None else 0

    # ?Have sun (solarbank)
    issbpion = sbpi>0  if sbpi is not None else None
    sbpion = sbpi[issbpion] if issbpion is not None and issbpion.any() else None
    sbpion_mean = sbpion.mean() if sbpion is not None else 0
    sbpion_max = sbpion.max() if sbpion is not None else 0

    # 'Have output (solarbank)
    issbpoon = sbpo>0 if sbpo is not None else None 
    sbpoon = sbpo[issbpoon] if issbpoon is not None and issbpoon.any() else None
    sbpoon_mean = sbpoon.mean() if sbpoon is not None else 0
    sbpoon_max = sbpoon.max() if sbpoon is not None else 0

    # ?Charging (solarbank)
    issbpbon = sbpb<0 if sbpb is not None else None 
    sbpbon = sbpb[issbpbon] if issbpbon is not None and issbpbon.any() else None
    sbpbon_mean = sbpbon.mean() if sbpbon is not None else 0
    sbpbon_min = sbpbon.min() if sbpbon is not None else 0

    # ?Discharging (solarbank)
    issbpboff = sbpb>0 if sbpb is not None else None  
    sbpboff = sbpb[issbpboff] if issbpboff is not None and issbpboff.any() else None
    sbpboff_mean = sbpboff.mean() if sbpboff is not None else 0
    sbpboff_max = sbpboff.max() if sbpboff is not None else 0
    
    timesbpion = time[issbpion] if issbpion is not None else None

    
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()

    if tphases is not None:
        ax.axvspan(tphases[0], tphases[1], 
                   color ='olive',
                   alpha = 0.2)        
        
    if spphon is not None:
        logger.info(f'using smartplug samples only')
        
        ax.fill_between(time, 0, spph,
                        color='grey',label='PLUG', lw=0, alpha=0.3)
        ax.fill_between(time, spph, spph + smpon,
                        color='b', label='GRID', lw=0, alpha=0.3)

    elif ivpon is not None:
        logger.info(f'using inverter samples only')
        
        ax.fill_between(time, 0, ivp1 + ivp2,
                        color='c', label='INV', alpha=0.2)
        ax.fill_between(time, ivp1 + ivp2, ivp1 + ivp2  + smpon,
                        color='b', label='GRID', alpha=0.3)

    elif sbpoon is not None:
        logger.info(f'using solarbank samples only')
        logger.warn(f'other power samples are ignored')

        ax.fill_between(time, 0, sbpo,
                        color='grey', label='BANK', lw=0, alpha=0.3)
        ax.fill_between(time, sbpo, sbpo + smpon,
                        color='b', label='GRID', lw=0, alpha=0.3)
        
    elif smpon is not None or smpoff is not None :
        logger.info(f'using smartmeter samples only')
        logger.warn(f'other power samples are not provided')

        ax.fill_between(time, 0, smp,
                        color='b', label='GRID', alpha=0.3)

        
    """ Plot the battery power of the solarbank during charging"""
    if sbpb is not None:
        """ The solarbank output is used directly inspite of inverter """
        ax.fill_between(time, 0, sbpb,
                        color='m', label='-BAT', alpha=0.3)
        sbpb_stacked = np.minimum(sbpb, [0])
        ax.fill_between(time, sbpb_stacked, sbpb_stacked + smpoff,
                        color='b', lw=0, alpha=0.3)

    else:
        ax.fill_between(time, 0, smpoff,
                        color='b', lw=0, alpha=0.3)


    if time.size<=24*60: #only plot within 24h
        if ivpon is not None:
            isfill = isivpon & ~issbpboff & ~issbpion
            ax.fill_between(time[isfill] ,
                            np.full_like(ivp[isfill], 600),
                            np.full_like(ivp[isfill], 800),
                            color='black', alpha=0.2)
        
        if sbpion is not None:
            isfill = issbpion & isivpon 
            ax.fill_between(time[isfill],
                            np.full_like(sbpi[isfill], 600),
                            np.full_like(sbpi[isfill], 800),
                            color='orange', label='LIMITS', alpha=0.4)
        
        
    title = f'# Power #\n'
    if sbpi is not None:
        title += f'Sun>{sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'

    if sbpoon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Bank>{sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
  
    if sbpb is not None:
        title += f' + {-sbpbon[-1] if sbpb[-1]<0 else 0:.0f}'
        title += f'={-sbpbon_mean:.0f}^{-sbpbon_min:.0f}W>'
        title += f'Bat'
        title += f'>{sbpboff[-1] if sbpb[-1]>0 else 0:.0f}'
        title += f'={sbpboff_mean:.0f}^{sbpboff_max:.0f}W'

    title += '' if title[-1] == '\n' else '\n'
        
    if ivpon is not None:
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'

    if spphon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug>{spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'

    if (smpoff is not None) or (smpon is not None):
        title += '' if title[-1] == '\n' else ' | '
        
        if (smpoff is not None) and (smpoff_min<0):
            title += f'{-smp[-1] if smp[-1]<0 else 0:.0f}'
            title += f'={-smpoff_mean:.0f}^{-smpoff_min:.0f}W>'

        title += f'Grid'

        if (smpon is not None) and (smpon_max>0):
            title += f'>{smp[-1] if smp[-1]>0 else 0:.0f}'
            title += f'={smpon_mean:.0f}^{smpon_max:.0f}W'
        
    ax.set_title(title)
    
    ax.legend(loc='upper left')
    ax.set_ylabel('Power [W]')
    ax.set_yscale('symlog')
    ax.xaxis_date()
    hm_formatter = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(hm_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='both')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')
