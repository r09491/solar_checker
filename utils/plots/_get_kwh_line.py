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

import numpy as np

import base64
from io import BytesIO

from datetime import datetime

from ..typing import (
    t64, t64s,
    f64, f64s, Any
)

TZ='Europe/Berlin'
XSIZE, YSIZE = 9, 6

POWER_PAYED = 12*44/0.279/365 #kWh
POWER_USED = (1010+532)/365 #kWh

def _get_kwh_line(
        time: t64s, smein: f64s, smeout: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh, full_kwh: f64s, price: f64,
        tphases: t64s = None,
        time_format: str = '%H:%M',
        tz: str = None):
    __me__ ='_get_kwh_line'
    logger.info(f'started')

    N = time.size

    ive1 = np.zeros(N) if ive1 is None else ive1
    ive2 = np.zeros(N) if ive2 is None else ive2
    ive = ive1 + ive2

    speh = np.zeros(N) if speh is None else speh
    sbei = np.zeros(N) if sbei is None else sbei
    sbeo = np.zeros(N) if sbeo is None else sbeo
    smein = np.zeros(N) if smein is None else smein
    smeout = np.zeros(N) if smeout is None else smeout
    sbebcharge = np.zeros(N) if sbebcharge is None else sbebcharge
    sbebdischarge = np.zeros(N) if sbebdischarge is None else sbebdischarge
    
    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.clear()

    if tphases is not None:
        # Selection Area
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

    # Stacked!
            
    if sbei.any():
        ax.fill_between(time, 0, sbei,
                        color='orange', label='SUN', alpha=0.3)

    if speh.any():
        ax.plot(time, speh,
                color='grey', label='PLUG', lw=1, ls='-', alpha=0.3)
        balcony = speh
        
    elif ive.any():
        ax.plot(time, ive,
                color='c',label='INV', lw=1, ls='-', alpha=0.3)
        balcony = ive
        
    elif sbeo.any():
        ax.plot(time, sbeo,
                color='grey',label='BANK', lw=1, ls='-', alpha=0.3)
        balcony = sbeo
        
    else:
        balcony = np.zeros(N)
        
    if smein.any():
        ax.fill_between(time, balcony, balcony + smein,
                        color='b',label='GRID', alpha=0.3)

        ax.axhline(balcony[-1] + POWER_PAYED,
                   label='PAYED', lw=2, color='orange', ls='--')
        ax.axhline(balcony[-1] + POWER_USED,
                   label='GOAL', lw=2, color='g', ls='--')        

        
    if sbsb is not None:
        ax.axhline(-empty_kwh, color='r', ls='--')        
        ax.axhline(-full_kwh, color='r', ls='--')

        sbeb = +sbebcharge - sbebdischarge + sbsb[0]

        ax.fill_between(time, 0, -sbsb,
                        color='m', label='BAT',alpha=0.3)

        ax.fill_between(time, -sbsb, -sbeb,
                        color='black', label='LOSS', alpha=0.3)

        ax.fill_between(time, -sbeb, -sbeb - smeout,
                        color='b', alpha=0.3)
        
    else:
        ax.fill_between(time, 0, -smeout,
                        color='b', alpha=0.3)


    title = f'# Energy #\n'
    if sbei.any():
        if time_format == '%H:%M': # Accumulated
            title += f'Sun>{sbei[-1]:.2f}kWh'
        else:
            title += f'Sun>{sbei.sum():.2f}kWh'
        title += '' if title[-1] == '\n' else ' | Bank> '
        if time_format == '%H:%M': # Accumulated
            if sbeo[-1] > 0:
                title += f' {sbeo[-1]:.2f}kWh'
        else:
            if sbeo.sum() > 0:
                title += f' {sbeo.sum():.2f}kWh~{sbeo.sum()*price:.2f}€'
        if (sbebcharge>0).any():
            title += '' if title[-1] == '\n' else ' + '
        
    if (sbebcharge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'{sbebcharge[sbebcharge>0][-1]:.2f}kWh>'
        else:
            title += f'{sbebcharge[sbebcharge>0].sum():.2f}kWh>'
    else:
        title += '' if title[-1] == '\n' else ' | '        

        
    if sbebdischarge.any():
        title += 'BAT'
    
    if (sbebdischarge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'>{sbebdischarge[sbebdischarge>0][-1]:.2f}kWh'
        else:
            title += f'>{sbebdischarge[sbebdischarge>0].sum():.2f}kWh'

    if sbsb is not None:
        title += f' #{sbsb[-1]:.2f}kWh~{sbsb[-1]/full_kwh*100:.0f}%'
            
            
    title += '' if title[-1] == '\n' else '\n'
        
    if speh.any():
        title += '' if title[-1] == '\n' else '\n'
        if time_format == '%H:%M': # Accumulated
            title += f'Plug>{speh[-1]:.2f}kWh~{speh[-1]*price:.2f}€'
        else:
            title += f'Plug>{speh.sum():.2f}kWh~{speh.sum()*price:.2f}€'

        balcony =speh
        
    elif ive.any():
        if time_format == '%H:%M': # Accumulated
            title += f'Inv>{ive[-1]:.2f}kWh~{ive[-1]*price:.2f}€'
        else:
            title += f'Inv>{ive.sum():.2f}kWh~{ive.sum()*price:.2f}€'

        balcony = ive
    else:
        balcony = np.zeros(N)
            
    title += '' if title[-1] == '\n' else ' | '            
            
    if smeout.any():
        if time_format == '%H:%M': # Accumulated
            if smeout[-1] > 0:
                title += f'{smeout[-1]:.2f}kWh~{(smeout[-1]*price):.2f}€>'
        else:
            if smeout.sum() > 0:
                title += f'{smeout.sum():.2f}kWh~{(smeout.sum()*price):.2f}€>'

    title += f'Grid'
    
    if smein.any():
        if time_format == '%H:%M': # Accumulated
            title += f'>{smein[-1]:.2f}kWh~{(smein[-1]*price):.2f}€'
        else:
            title += f'>{smein.sum():.2f}kWh~{(smein.sum()*price):.2f}€'

    if balcony.any() and (smeout is not None):            
        if time_format == '%H:%M': # Accumulated
            title += f' # Bonus {(balcony[-1]-smeout[-1]):.2f}kWh~{(balcony[-1]-smeout[-1])*price:.2f}€'
        else:
            title += f' # Bonus {balcony.sum()-smeout.sum():.2f}kWh~{(balcony.sum()-smeout.sum())*price:.2f}€'


    ax.set_title(title)

    ax.legend(loc="best")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format, tz=tz)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='both')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'done')

    return base64.b64encode(buf.getbuffer()).decode('ascii')
