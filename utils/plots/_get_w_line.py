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
    issmpin = smp>0 if smp is not None else None
    smpin = np.zeros_like(smp) if issmpin is not None else None
    smpin[issmpin] = smp[issmpin] if issmpin is not None else None 
    smpin_mean = 0 if (smpin is None or
                       not issmpin.any()) else smpin.mean()
    smpin_max = 0 if (smpin is None or
                      not issmpin.any()) else smpin.max()

    issmpout = smp<0 if smp is not None else None
    smpout = np.zeros_like(smp) if issmpout is not None else None
    smpout[issmpout] = smp[issmpout] if issmpout is not None else None 
    smpout_mean = 0 if (smpout is None or
                        not issmpout.any()) else smpout.mean()
    smpout_min = 0 if (smpout is None or
                       not issmpout.any()) else smpout.min()

    # ?Have data (inverter)
    ivp = ivp1 + ivp2 if ivp1 is not None and ivp2 is not None else None
    isivpon = ivp>0 if ivp is not None else None 
    ivpon = ivp if isivpon is not None else None 
    ivpon_mean = 0 if (ivpon is None or
                       not isivpon.any()) else ivpon.mean()
    ivpon_max = 0 if (ivpon is None or
                      not isivpon.any()) else ivpon.max()

    # ?Have power ( smartplug)
    isspphon = spph>0 if spph is not None else None
    spphon = spph if isspphon is not None else None
    spphon_mean = 0 if (spphon is None or
                        not isspphon.any()) else spphon.mean()
    spphon_max = 0 if (spphon is None or
                       not isspphon.any()) else spphon.max()

    # ?Have sun (solarbank)
    issbpion = sbpi>0 if sbpi is not None else None
    sbpion = sbpi[issbpion] if issbpion is not None else None
    sbpion_mean = sbpion.mean() if (sbpion is not None and
                                    issbpion.any()) else 0
    sbpion_max = sbpion.max() if (sbpion is not None and
                                  issbpion.any()) else 0

    # 'Have output (solarbank)
    issbpoon = sbpo>0 if sbpo is not None else None
    sbpoon = sbpo if issbpoon is not None else None
    sbpoon_mean = sbpoon.mean() if (sbpoon is not None and
                                    issbpoon.any()) else 0
    sbpoon_max = sbpoon.max() if (sbpoon is not None and
                                  issbpoon.any()) else 0

    # ?Charging (solarbank)
    issbpbin = sbpb<0 if sbpb is not None else None
    sbpbin = np.zeros_like(sbpb) if issbpbin is not None else None
    sbpbin[issbpbin] = sbpb[issbpbin] if issbpbin is not None else None 
    sbpbin_mean = 0 if (sbpbin is None or
                        not issbpbin.any()) else sbpbin.mean()
    sbpbin_min = 0 if (sbpbin is None or
                       not issbpbin.any()) else sbpbin.min()

    # ?Discharging (solarbank)
    issbpbout = sbpb>0 if sbpb is not None else None
    sbpbout = np.zeros_like(sbpb) if issbpbout is not None else None
    sbpbout[issbpbout] = sbpb[issbpbout] if issbpbout is not None else None 
    sbpbout_mean = 0 if (sbpbout is None or
                         not issbpbout.any()) else sbpbout.mean()
    sbpbout_max = 0 if (sbpbout is None or
                        not issbpbout.any()) else sbpbout.max()

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
    if issbpion is not None and issbpion.any():
        isfill = issbpion|np.roll(issbpion,-1)|np.roll(issbpion,+1)
        ax.fill_between(time, 0, sbpi,
                        where = isfill,
                        color='yellow', label='SUN', lw=1, alpha=0.3)

        ax.fill_between(time, sbpi, sbpi + smpin,
                        where = isfill,
                        color='b', lw=1, alpha=0.3)

        if issmpin is not None:
            issmpin &= ~isfill #~issbpion

        if time.size<=24*60: #only plot within 24h
            ax.fill_between(time[issbpion],
                            np.full_like(sbpion, 600),
                            np.full_like(sbpion, 800),
                            color='red', label='LIMITS', alpha=0.2)

    if issmpin is not None: #import
        isfill = issmpin|np.roll(issmpin,-1)|np.roll(issmpin,+1)
        ax.fill_between(time, 0, smpin,
                        where = isfill,
                        color='b', label='GRID', lw=1, alpha=0.3)

        
    if issbpbin is not None and issbpbin.any(): #charge
        isfill = issbpbin|np.roll(issbpbin,-1)|np.roll(issbpbin,+1)
        ax.fill_between(time, sbpbin, 0,
                        where = isfill,
                        color='m', label='BAT', alpha=0.3)
        ax.fill_between(time, sbpbin+smpout, sbpbin, 
                        where = isfill,
                        color='b', lw=0, alpha=0.3)
        issmpout &= ~issbpbin

    if issmpout is not None and issmpout.any(): #export
        isfill = issmpout|np.roll(issmpout,-1)|np.roll(issmpout,+1)
        ax.fill_between(time, 0, smpout,
                        where = isfill,
                        color='b', lw=0, alpha=0.3)

    if issbpbout is not None and issbpbout.any(): #discharge
        isfill = issbpbout|np.roll(issbpbout,-1)|np.roll(issbpbout,+1)
        ax.fill_between(time, sbpbout, 0,
                        where = isfill,
                        color='m', alpha=0.3)
        
    
    """ Plot amplifying data as lines """

    if spphon is not None and spphon.any():
        ax.plot(time, spph,
                color='brown', lw=2, ls='-', alpha=0.4)
    if ivpon is not None and ivpon.any():
        ax.plot(time, ivp,
                color='c', lw=2, ls='-', alpha=0.4)
    if sbpoon is not None and sbpoon.any():
        ax.plot(time, sbpo,
                color='grey', lw=2, ls='-', alpha=0.4)


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
        
    if ivpon is not None and np.any(ivpon):
        title += f'Inv>{ivp[-1]:.0f}'
        title += f'={ivpon_mean:.0f}^{ivpon_max:.0f}W'

    if spphon is not None and np.any(spphon):
        title += '' if title[-1] == '\n' else ' | '
        title += f'Plug>{spph[-1]:.0f}'
        title += f'={spphon_mean:.0f}^{spphon_max:.0f}W'

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
