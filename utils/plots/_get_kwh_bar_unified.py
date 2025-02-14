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

def _get_kwh_bar_unified(
        time: t64s, smeon: f64s, smeoff: f64s, balcony: f64s,
        price: f64, bar_width: f64, time_format: str):

    __me__='_get_kwh_bar_unified'
    logger.info(f'started')

    balconyon = balcony[balcony>0] if balcony is not None else None

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE+1))

    ax.clear()

    if balconyon is not None:
        logger.info(f'using unified samples')

        ax.bar(time, balcony, bottom = smeoff,
               color='cyan', label='BALCONY', width=bar_width, alpha=0.3)
        ax.bar(time, smeon, bottom=balcony+smeoff,
               color='blue',label='GRID >', width=bar_width, alpha=0.3)

        for x, ysmeoff, ybalcony, ysmeon in zip(time, smeoff, balcony, smeon):
            if ybalcony > 0.5 and ysmeoff < 0.0:
                ax.text(x, ysmeoff, f'{ybalcony:.1f}', ha = 'center',
                        color = 'grey', weight='bold', size=8)

            if ysmeoff + ybalcony > 0.5:
                ax.text(x, (ysmeoff + ybalcony)/2, f'{ysmeoff+ybalcony:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)
            if ysmeon > 1.0:
                ax.text(x, ysmeoff + ybalcony + ysmeon/2 , f'{ysmeon:.1f}', ha = 'center',
                        color = 'black', weight='bold', size=8)

    else:
        logger.info(f'using smartmeter samples only')

        if smeon is not None:
            ax.bar(time, smeoff, bottom = 0,
                   color='blue', width=bar_width, alpha=0.3)
        if smeoff is not None:
            ax.bar(time, smeon, bottom=balcony,
                   color='blue',label='GRID', width=bar_width, alpha=0.3)
            
                
    title = f'# Energy Check #\n'
    if balconyon.any():
        title += f'Balcony>{balconyon.sum():.1f}'
        title += f'={balconyon.mean():.1f}'
        title += f'^{balconyon.max():.1f}kWh'
        title += f'~{balconyon.sum()*price:.2f}€'

    smeonon = smeon[smeon>0]
    if smeonon.any():
        
        smeoffon = abs(smeoff)[abs(smeoff)>0]
        if smeoffon.any():
            title += f' | Profit {(balconyon.sum()-smeoffon.sum()):.1f}kWh'
            title += f'~{((balconyon.sum()-smeoffon.sum())*price):.2f}€'
            title += f' ({(balconyon.sum()-smeoffon.sum())/balconyon.sum()*100:.0f}%)'
                
            #title += f' | Gift {smeoffon.sum():.1f}kWh'
            #title += f'~{smeoffon.sum()*price:.2f}€'
            #title += f' ({smeoffon.sum()/balconyon.sum()*100:.0f}%)'

            title += f'\n{smeoffon.sum():.1f}'
            title += f'={smeoffon.mean():.1f}'
            title += f'^{smeoffon.max():.1f}kWh'   
            title += f'~{(smeoffon.sum()*price):.2f}€>'
        else:
            title += '\n'

        title += f'Grid'
            
        title += f'>{smeonon.sum():.1f}'
        title += f'={smeonon.mean():.1f}'
        title += f'^{smeonon.max():.1f}kWh'   
        title += f'~{(smeonon.sum()*price):.2f}€'

    ax.set_title(title, fontsize='x-large')

    ax.legend(loc="upper right")
    ax.set_ylabel('Energy [kWh]')
    ax.xaxis_date()
    ax_formatter = mdates.DateFormatter(time_format)
    ax.xaxis.set_major_formatter(ax_formatter)
    ax.grid(which='major', ls='-', lw=1, axis='y')
    ax.grid(which='major', ls=':', lw=1, axis='x')
    ax.grid(which='minor', ls=':', lw=1, axis='both')
    ax.minorticks_on()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')
