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
    smpin[issmpin] = smp[issmpin] if issmpin is not None else None 
    smpin_mean = 0 if not issmpin.any() else smpin.mean()
    smpin_max = 0 if not issmpin.any() else smpin.max()

    smpout = np.zeros_like(smp) if smp is not None else None
    issmpout = smp<0 if smp is not None else None
    smpout[issmpout] = smp[issmpout] if issmpout is not None else None 
    smpout_mean = 0 if not issmpout.any() else smpout.mean()
    smpout_min = 0 if not issmpout.any() else smpout.min()

    # ?Have data (inverter)
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp2 is not None else np.zeros_like(smp) 
    isivpon = ivp>0
    ivpon = ivp[isivpon]
    ivpon_mean = ivpon.mean() if ivpon.any() else 0
    ivpon_max = ivpon.max() if ivpon.any() else 0

    # ?Have power ( smartplug)
    spph = spph if spph is not None else np.zeros_like(smp) 
    isspphon = spph>0
    spphon = spph[isspphon]
    spphon_mean = spphon.mean() if spphon.any() else 0
    spphon_max = spphon.max() if spphon.any() else 0

    # ?Have sun (solarbank)
    sbpi = sbpi if sbpi is not None else np.zeros_like(smp)
    issbpion = sbpi>0
    sbpion = sbpi[issbpion]
    sbpion_mean = sbpion.mean() if sbpion.any() else 0
    sbpion_max = sbpion.max() if sbpion.any() else 0

    # 'Have output (solarbank)
    sbpo = sbpo if sbpo is not None else np.zeros_like(smp)
    issbpoon = sbpo>0
    sbpoon = sbpo[issbpoon]
    sbpoon_mean = sbpoon.mean() if sbpoon.any() else 0
    sbpoon_max = sbpoon.max()  if sbpoon.any() else 0

    # ?Charging (solarbank)
    sbpbin = np.zeros_like(sbpb) if sbpb is not None else None
    issbpbin = sbpb<0 if sbpb is not None else None
    sbpbin[issbpbin] = sbpb[issbpbin] if issbpbin is not None else None 
    sbpbin_mean = 0 if not issbpbin.any() else sbpbin.mean()
    sbpbin_min = 0 if not issbpbin.any() else sbpbin.min()

    # ?Discharging (solarbank)
    sbpbout = np.zeros_like(sbpb) if sbpb is not None else None
    issbpbout = sbpb>0 if sbpb is not None else None
    sbpbout[issbpbout] = sbpb[issbpbout] if issbpbout is not None else None 
    sbpbout_mean = 0 if not issbpbout.any() else sbpbout.mean()
    sbpbout_max = 0 if not issbpbout.any() else sbpbout.max()

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
                color ='olive',
                alpha = 0.1
            )        

    """ Plot solarbank and smartmeter filled """
    if np.any(sbpoon):
        isfill = issbpoon|np.roll(issbpoon,1)|np.roll(issbpoon,-1)
        ax.fill_between(time, 0, sbpo,
                        where = isfill,
                        color='grey', label='BANK', lw=1, alpha=0.3)
        ax.fill_between(time, sbpo, sbpo + smpin,
                        where = isfill,
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~isfill 
        isivpon &= ~isfill
        isspphon &= ~isfill

    if np.any(ivpon):
        isfill = isivpon|np.roll(isivpon,1)|np.roll(isivpon,-1)
        ax.fill_between(time, 0, ivp,
                        where = isfill,
                        color='c', label='INV', lw=1, alpha=0.3)
        ax.fill_between(time, ivp, ivp + smpin,
                        where = isfill,
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~isfill
        isspphon &= ~isfill

    if np.any(spphon):
        isfill = isspphon|np.roll(isspphon,1)|np.roll(isspphon,-1)
        ax.fill_between(time, 0, spph,
                        where = isfill,
                        color='brown', label='PLUG', lw=1, alpha=0.3)
        ax.fill_between(time, spph, spph + smpin,
                        where = isfill,
                        color='b', lw=1, alpha=0.3)
        issmpin &= ~isfill
   

    if np.any(smpin): #import
        isfill = issmpin|np.roll(issmpin,1)|np.roll(issmpin,-1)
        ax.fill_between(time, 0, smpin,
                        where = isfill,
                        color='b', label='GRID', lw=1, alpha=0.3)
        issmpout &= ~isfill
        
    """ Plot the battery power of the solarbank during charging"""

    if np.any(sbpbin): #charge
        isfill = issbpbin|np.roll(issbpbin,1)|np.roll(issbpbin,-1)
        ax.fill_between(time, sbpbin, 0,
                        where = isfill,
                        color='m', label='BAT', alpha=0.3)
        ax.fill_between(time, sbpbin+smpout, sbpbin, 
                        where = isfill,
                        color='b', lw=0, alpha=0.3)
        issmpout &= ~isfill

    if np.any(smpout): #export
        isfill = issmpin|np.roll(issmpin,1)|np.roll(issmpin,-1)
        ax.fill_between(time, 0, smpout,
                        where = isfill,
                        color='b', lw=0, alpha=0.3)

    if np.any(sbpbout): #discharge
        isfill = issbpbout|np.roll(issbpbout,1)|np.roll(issbpbout,-1)
        ax.fill_between(time, sbpbout, 0,
                        where = isfill,
                        color='m', alpha=0.3)
        
    
    """ Plot amplifying data as lines """

    if np.any(spphon):
        ax.plot(time, spph,
                color='brown',label='PLUG', lw=2, ls='-', alpha=0.3)
    if np.any(ivpon):
        ax.plot(time, ivp,
                color='c', label='INV', lw=2, ls='-', alpha=0.3)
    if np.any(sbpion):
        ax.plot(time[issbpion], sbpi[issbpion],
                color='orange', label='SUN', lw=2, ls='-', alpha=0.8)
        if time.size<=24*60: #only plot within 24h
            ax.fill_between(time[issbpion],
                            np.full_like(sbpion, 600),
                            np.full_like(sbpion, 800),
                            color='black', label='LIMITS', alpha=0.1)

    """ Generate title """
            
    title = f'# Power #\n'
    if np.any(sbpi) and (sbpion_max>0):
        # There is irradation
        title += f'Sun>{sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'
        title += '' if title[-1] == '\n' else ' | Bank>'
        title += f' {sbpo[-1]:.0f}'
        title += f'={sbpoon_mean:.0f}^{sbpoon_max:.0f}W'
        if (sbpbout is not None) or (sbpbin is not None):
           title += f' + '
    if np.any(sbpbin) and (sbpbin_min<0):
        title += f'{-sbpbin[-1] if sbpb[-1]<0 else 0:.0f}'
        title += f'={-sbpbin_mean:.0f}^{-sbpbin_min:.0f}W>'
    if np.any(sbpbin) or np.any(sbpbout):
        title += f'Bat'
    if np.any(sbpbout) and (sbpbout_max>0):
        title += f'>{sbpbout[-1] if sbpb[-1]>0 else 0:.0f}'
        title += f'={sbpbout_mean:.0f}^{sbpbout_max:.0f}W'

    title += '' if title[-1] == '\n' else '\n'
        
    if np.any(ivpon):
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'

    if np.any(spphon):
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug>{spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'

    if np.any(smpout) or np.any(smpin):
        title += '' if title[-1] == '\n' else ' | '
        
        if np.any(smpout) and (smpout_min<0):
            title += f'{-smp[-1] if smp[-1]<0 else 0:.0f}'
            title += f'={-smpout_mean:.0f}^{-smpout_min:.0f}W>'

        title += f'Grid'

        if np.any(smpin) and (smpin_max>0):
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
