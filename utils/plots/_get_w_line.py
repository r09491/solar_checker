import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(__name__)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.dates import date2num
import numpy as np

import base64
from io import BytesIO

from datetime import datetime

from ..typing import (
    t64, t64s,
    f64, f64s, Any
)

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

TZ='Europe/Berlin'
XSIZE, YSIZE = 9, 6

def _get_w_line(time: t64s, smp: f64s,
                ivp1: f64s, ivp2: f64s, spph: f64s,
                sbpi: f64s, sbpo: f64s, sbpb: f64s,
                tphases: t64s = None,
                tz: str = None):
    __me__ ='_get_w_line'
    logger.info(f'started')

    # ?Have data (smartmeter)
    smpin = np.zeros_like(smp) if smp is not None else None
    issmpin = smp>0 if smp is not None else None
    smpin[issmpin] = smp[issmpin] 
    smpin_mean = 0 if not issmpin.any() else smpin.mean()
    smpin_max = 0 if not issmpin.any() else smpin.max()

    smpout = np.zeros_like(smp) if smp is not None else None
    issmpout = smp<0 if smp is not None else None
    smpout[issmpout] = smp[issmpout] 
    smpout_mean = 0 if not issmpout.any() else smpout.mean()
    smpout_min = 0 if not issmpout.any() else smpout.min()

    # ?Have data (inverter)
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp2 is not None else np.zeros_like(smp) 
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
    issbpbin = sbpb<0 if sbpb is not None else None 
    sbpbin = sbpb[issbpbin] if issbpbin is not None and issbpbin.any() else None
    sbpbin_mean = sbpbin.mean() if sbpbin is not None else 0
    sbpbin_min = sbpbin.min() if sbpbin is not None else 0

    # ?Discharging (solarbank)
    issbpbout = sbpb>0 if sbpb is not None else None  
    sbpbout = sbpb[issbpbout] if issbpbout is not None and issbpbout.any() else None
    sbpbout_mean = sbpbout.mean() if sbpbout is not None else 0
    sbpbout_max = sbpbout.max() if sbpbout is not None else 0
    
    timesbpion = time[issbpion] if issbpion is not None else None

    
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))
    
    ax.clear()

    if tphases is not None:
        # Selection area
        ax.axvspan(
            mdates.date2num(tphases[0]),
            mdates.date2num(tphases[1]), 
            color ='olive',
            alpha = 0.3
        )
        # Cast area
        if len(tphases)>2:
            ax.axvspan(
                mdates.date2num(tphases[2]),
                mdates.date2num(tphases[3]), 
                color ='white',
                alpha = 0.6
            )        

    
    """ Plot solarbank and smartmeter filled """
    
    if sbpoon is not None and np.any(sbpoon):
        ax.fill_between(time, 0, sbpo,
                        where = issbpoon,
                        color='grey', label='BANK', lw=1, alpha=0.3)
        ax.fill_between(time, sbpo, sbpo + smpin,
                        where = issbpoon,
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~issbpoon
        
    if ivpon is not None and np.any(ivpon):
        ax.fill_between(time, 0, ivp,
                        where = isivpon & ~issbpoon,
                        color='c', label='INV', lw=1, alpha=0.3)
        ax.fill_between(time, ivp, ivp + smpin,
                        where = isivpon & ~issbpoon,
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~isivpon

    if spphon is not None and np.any(spphon):
        ax.fill_between(time, 0, spph,
                        where = isspphon & ~(issbpoon | isivpon),
                        color='brown', label='PLUG', lw=1, alpha=0.3)
        ax.fill_between(time, spph, spph + smpin,
                        where = isspphon & ~(issbpoon | isivpon),
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~isspph

    if smpin is not None:
        ax.fill_between(time, 0, smpin,
                        where = issmpin,
                        color='b', label='GRID', lw=1, alpha=0.3)

    """ Plot the battery power of the solarbank during charging"""

    if sbpb is not None and np.any(sbpb):
        ax.fill_between(time, 0, sbpb,
                        #where = issbpbout,
                        color='m', label='BAT', alpha=0.3)
        ax.fill_between(time, np.minimum(sbpb,[0]),
                        np.minimum(sbpb,[0]) + smpout,
                        where = issbpbout,
                        color='b', lw=0, alpha=0.3)


    """ Plot amplifying data as lines """

    if spph is not None and np.any(spph):
        ax.plot(time, spph,
                color='brown',label='PLUG', lw=2, ls='-', alpha=0.3)
    if ivp is not None and np.any(ivp):
        ax.plot(time, ivp,
                color='c', label='INV', lw=2, ls='-', alpha=0.3)
    if sbpion is not None and np.any(sbpion):
        if time.size<=24*60: #only plot within 24h
            issun = np.where(issbpion)[0]
            start, stop = issun[0], issun[-1]
            ax.plot(time[start:stop], sbpi[start:stop],
                    color='orange', label='SUN', lw=2, ls='-', alpha=0.8)
            ax.fill_between(time[issbpion],
                            np.full_like(sbpi[issbpion], 600),
                            np.full_like(sbpi[issbpion], 800),
                            color='black', label='LIMITS', alpha=0.2)

    """ Generate title """
            
    title = f'# Power #\n'
    if (sbpi is not None) and (sbpion_max>0):
        # There is irradation
        title += f'Sun>{sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'
        title += '' if title[-1] == '\n' else ' | Bank>'
        title += f' {sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
        if (sbpbout is not None) or (sbpbin is not None):
           title += f' + '
    if (sbpbin is not None) and (sbpbin_min<0):
        title += f'{-sbpbin[-1] if sbpb[-1]<0 else 0:.0f}'
        title += f'={-sbpbin_mean:.0f}^{-sbpbin_min:.0f}W>'
    if (sbpbin is not None) or (sbpbout is not None):
        title += f'Bat'
    if (sbpbout is not None) and (sbpbout_max>0):
        title += f'>{sbpbout[-1] if sbpb[-1]>0 else 0:.0f}'
        title += f'={sbpbout_mean:.0f}^{sbpbout_max:.0f}W'

    title += '' if title[-1] == '\n' else '\n'
        
    if ivpon is not None:
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'

    if spphon is not None:
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug>{spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'

    if (smpout is not None) or (smpin is not None):
        title += '' if title[-1] == '\n' else ' | '
        
        if (smpout is not None) and (smpout_min<0):
            title += f'{-smp[-1] if smp[-1]<0 else 0:.0f}'
            title += f'={-smpout_mean:.0f}^{-smpout_min:.0f}W>'

        title += f'Grid'

        if (smpin is not None) and (smpin_max>0):
            title += f'>{smp[-1] if smp[-1]>0 else 0:.0f}'
            title += f'={smpin_mean:.0f}^{smpin_max:.0f}W'
        
    ax.set_title(title)
    
    ax.legend(loc='upper left')
    ax.set_ylabel('Power [W]')
    ax.set_yscale('symlog')
    ax.xaxis_date()
    hm_formatter = mdates.DateFormatter('%H:%M', tz=tz)
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
