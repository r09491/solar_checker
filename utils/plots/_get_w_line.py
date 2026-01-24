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

    # Number of samples
    N = time.size
    
    # ?Have data (smartmeter)
    smp = np.zeros(N) if smp is None else smp

    issmpin = smp>0
    smpin = np.zeros_like(smp)
    smpin[issmpin] = smp[issmpin]
    smpin_mean = smpin.mean()
    smpin_max = smpin.max()

    issmpout = smp<0
    smpout = np.zeros_like(smp)
    smpout[issmpout] = smp[issmpout]
    smpout_mean = smpout.mean()
    smpout_min = smpout.min()

    # ?Have data (inverter)
    ivp1 = np.zeros(N) if ivp1 is None else ivp1
    ivp2 = np.zeros(N) if ivp2 is None else ivp2

    ivp = ivp1 + ivp2
    isivpon = ivp>0
    ivp_mean = ivp.mean()
    ivp_max = ivp.max()

    # ?Have power ( smartplug)
    spph = np.zeros(N) if spph is None else spph
    
    isspphon = spph>0
    spph_mean = spph.mean()
    spph_max = spph.max()

    # ?Have sun (solarbank)
    sbpi = np.zeros(N) if sbpi is None else sbpi
        
    issbpion = sbpi>0
    sbpion = sbpi
    sbpion[issbpion] = sbpi[issbpion]
    sbpion_mean = sbpion.mean()
    sbpion_max = sbpion.max() 

    # 'Have output (solarbank)
    sbpo = np.zeros(N) if sbpo is None else sbpo

    issbpoon = sbpo>0
    sbpo_mean = sbpo.mean()
    sbpo_max = sbpo.max()


    sbpb = np.zeros(N) if sbpb is None else sbpb

    # ?Charging (solarbank)
    issbpbin = sbpb<0
    sbpbin = np.zeros_like(sbpb)
    sbpbin[issbpbin] = sbpb[issbpbin]
    sbpbin_mean = sbpbin.mean()
    sbpbin_min = sbpbin.min()

    # ?Discharging (solarbank)
    issbpbout = sbpb>0
    sbpbout = np.zeros_like(sbpb)
    sbpbout[issbpbout] = sbpb[issbpbout]
    sbpbout_mean = sbpbout.mean()
    sbpbout_max = sbpbout.max()

    
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


    """ Plot positive sample segmants """

    stage = 0 #np.zeros_like(smp)


    ax.plot(time, spph, color='grey', lw=3, ls='-', alpha=0.3)

    spph[isivpon|issbpion|issbpbout] = 0
    if spph.any():
        ax.fill_between(
            time,
            stage, stage + spph,
            color='grey', lw=0, alpha=0.2, label='PLUG'
        )
        stage += spph


    ax.plot(time, ivp, color='c', lw=3, ls='-', alpha=0.3)

    ivp[issbpion|issbpbout] =0
    if ivp.any():
        ax.fill_between(
            time,
            stage, stage + ivp,
            color='c', lw=0, alpha=0.2, label='INV'
        )
        stage += ivp


    sbpi[issbpbout] =0
    if sbpi.any():
        ax.fill_between(
            time,
            stage, stage + sbpi,
            color='orange', lw=0, alpha=0.3, label='SUN'
        )
        stage += sbpi

        ax.fill_between(
            time[issbpion],
            np.full_like(sbpi[issbpion], 600),
            np.full_like(sbpi[issbpion], 800),
            color='red', alpha=0.2
        )
        

    if sbpbout.any():
        ax.fill_between(
            time,
            stage, stage + sbpbout,
            color='m', lw=0, alpha=0.3, label='BAT'
        )
        stage += sbpbout


    if smpin.any():
        ax.fill_between(
            time,
            stage, stage + smpin,
            color='b', lw=0, alpha=0.3, label='GRID'
        )

    """ Plot negative sample segmants"""

    ax.fill_between(time, 0, sbpbin,
                    color='m', lw=0, alpha=0.3)
    ax.fill_between(time, sbpbin, sbpbin + smpout,
                    color='b', lw=0, alpha=0.3)
    
    """ Plot amplifying data as lines """

    if spph.any():
        ax.plot(time, spph,
                color='grey', lw=3, ls='-', alpha=0.3)


    """ Generate title """
            
    title = f'# Power #\n'
    if np.any(sbpi) and (sbpion_max>0):
        # There is irradation
        title += f'Sun>{sbpi[-1]:.0f}'
        title += f'={sbpion_mean:.0f}^{sbpion_max:.0f}W'
        title += '' if title[-1] == '\n' else ' | Bank>'
        title += f' {sbpo[-1]:.0f}'
        title += f'={sbpo_mean:.0f}^{sbpo_max:.0f}W'
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
        
    if np.any(ivp):
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivp_mean:.0f}^{ivp_max:.0f}W'

    if np.any(spph):
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug>{spph[-1]:.0f}'
        title += f'={spph_mean:.0f}^{spph_max:.0f}W'

    if ((smpout is not None and np.any(smpout)) or
        (smpin is not None and np.any(smpin))):
        title += '' if title[-1] == '\n' else ' | '
        
        if np.any(smpout) and (smpout_min<0):
            title += f'{-smp[-1] if smp[-1]<0 else 0:.0f}'
            title += f'={-smpout_mean:.0f}^{-smpout_min:.0f}W>'

        title += f'Grid'

        if np.any(smpin) and (smpin_max>0):
            title += f'>{smp[-1] if smp[-1]>0 else 0:.0f}'
            title += f'={smpin_mean:.0f}^{smpin_max:.0f}W'
        
    ax.set_title(title)
    
    ax.legend(loc='best')
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
