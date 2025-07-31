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

XSIZE, YSIZE = 10, 5

def _get_kwh_line(
        time: t64s, smeon: f64s, smeoff: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh, full_kwh: f64s, price: f64,
        tphases: t64s = None,
        time_format: str = '%H:%M'):
    __me__ ='_get_kwh_line'
    logger.info(f'started')

    ive = ive1 + ive2 if ive1 is not None and ive1 is not None else None 
    isiveon = ive>0 if ive is not None else None
    iveon = ive[isiveon] if isiveon is not None and isiveon.any() else None

    isspehon = speh>0 if speh is not None else None
    spehon = speh[isspehon] if isspehon is not None and isspehon.any() else None

    issbeion = sbei>0 if sbei is not None else None
    sbeion = sbei[issbeion] if issbeion is not None and issbeion.any() else None

    issbeoon = sbeo>0 if sbeo is not None else None
    sbeoon = sbeo[issbeoon] if issbeoon is not None and issbeoon.any() else None

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
                color ='white',
                alpha = 0.6
            )        

    
    if sbeoon is not None:
        ax.fill_between(time, 0, sbeo,
                        color='grey', label='BANK',alpha=0.3)
        ax.fill_between(time, sbeo, sbeo + smeon,
                        color='b',label='GRID', alpha=0.3)

    elif smeon is not None:
        ax.fill_between(time, smeoff, smeon,
                        color='b',label='GRID', alpha=0.3)

        
    if sbsb is not None:
        ax.axhline(-empty_kwh, color='r', ls='--')        
        ax.axhline(-full_kwh, color='r', ls='--')

        sbeb = +sbebcharge - sbebdischarge + sbsb[0]

        ax.fill_between(time, 0, -sbsb,
                        color='m', label='-BAT',alpha=0.3)

        ax.fill_between(time, -sbsb, -sbeb,
                        color='black', label='LOSS', alpha=0.3)

        ax.fill_between(time, -sbeb, -sbeb - smeoff,
                        color='b', alpha=0.3)
        
    else:
        ax.fill_between(time, 0, -smeoff,
                        color='b', alpha=0.3)

        
    if spehon is not None:
        ax.plot(time, speh,
                color='brown', label='PLUG', lw=2, ls='-', alpha=0.6)
    if iveon is not None:
        ax.plot(time, ive2 + ive1,
                color='c',label='INV', lw=2, ls='-', alpha=0.6)                             
    if sbeion is not None:
        ax.plot(time[issbeion], sbei[issbeion],
                color='orange', label='SUN', lw=2, ls='-', alpha=0.8)

        
    title = f'# Energy #\n'
    if sbeion is not None:
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
        if (sbebcharge is not None) and ((sbebcharge>0).any()):
            title += '' if title[-1] == '\n' else ' + '
        
    if (sbebcharge is not None) and (sbebcharge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'{sbebcharge[sbebcharge>0][-1]:.2f}kWh>'
        else:
            title += f'{sbebcharge[sbebcharge>0].sum():.2f}kWh>'
    else:
        title += '' if title[-1] == '\n' else ' | '        

        
    if (sbebcharge is not None) or (sbebdischarge is not None):
        title += 'BAT'
    
    if (sbebdischarge is not None) and (sbebdischarge>0).any():
        if time_format == '%H:%M': # Accumulated
            title += f'>{sbebdischarge[sbebdischarge>0][-1]:.2f}kWh'
        else:
            title += f'>{sbebdischarge[sbebdischarge>0].sum():.2f}kWh'

    if sbsb is not None:
        title += f' #{sbsb[-1]:.2f}kWh~{sbsb[-1]/full_kwh*100:.0f}%'
            
            
    title += '' if title[-1] == '\n' else '\n'
        
    if iveon is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'Inv>{ive[-1]:.2f}kWh~{ive[-1]*price:.2f}€'
        else:
            title += f'Inv>{ive.sum():.2f}kWh~{ive.sum()*price:.2f}€'

    if spehon is not None:
        title += '' if title[-1] == '\n' else '\n'
        if time_format == '%H:%M': # Accumulated
            title += f'Plug>{speh[-1]:.2f}kWh~{speh[-1]*price:.2f}€'
        else:
            title += f'Plug>{speh.sum():.2f}kWh~{speh.sum()*price:.2f}€'

            
    title += '' if title[-1] == '\n' else ' | '            
            
    if smeoff is not None:
        if time_format == '%H:%M': # Accumulated
            if smeoff[-1] > 0:
                title += f'{smeoff[-1]:.2f}kWh~{(smeoff[-1]*price):.2f}€>'
        else:
            if smeoff.sum() > 0:
                title += f'{smeoff.sum():.2f}kWh~{(smeoff.sum()*price):.2f}€>'

    title += f'Grid'
    
    if smeon is not None:
        if time_format == '%H:%M': # Accumulated
            title += f'>{smeon[-1]:.2f}kWh~{(smeon[-1]*price):.2f}€'
        else:
            title += f'>{smeon.sum():.2f}kWh~{(smeon.sum()*price):.2f}€'

    if (iveon is not None) and (smeoff is not None):            
        if time_format == '%H:%M': # Accumulated
            title += f' # Bonus {(ive[-1]-smeoff[-1]):.2f}kWh~{(ive[-1]-smeoff[-1])*price:.2f}€'
        else:
            title += f' # Bonus {ive.sum()-smeoff.sum():.2f}kWh~{(ive.sum()-smeoff.sum())*price:.2f}€'
    elif (sbeoon is not None) and (smeoff is not None):            
        if time_format == '%H:%M': # Accumulated
            title += f' # Bonus {(sbeo[-1]-smeoff[-1]):.2f}kWh~{(sbeo[-1]-smeoff[-1])*price:.2f}€'
        else:
            title += f' # Bonus {sbeo.sum()-smeoff.sum():.2f}kWh~{(sbeo.sum()-smeoff.sum())*price:.2f}€'

    ax.set_title(title)

    ax.legend(loc="upper left")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
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
