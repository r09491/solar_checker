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

def _get_blocks(time: t64, smp: f64,
                ivp1: f64, ivp2: f64, spph: f64,
                sbpi: f64, sbpo: f64, sbpb: f64,
                spp1: f64, spp2: f64, spp3: f64, spp4: f64):
    __me__ ='_blocks'
    logger.info(f'started')

    fig, ax = plt.subplots(nrows=1,figsize=(XSIZE, YSIZE))

    ax.axis('equal')
    ax.axis('off')

    # Kann be anything! Only for relations
    BW, BH = 2, 2
    
    def _add_link_to_ax(ax: Any,
                        xb0: int, yb0: int, gate0: str,
                        xb1: int, yb1: int, gate1: str,
                        power: float, color: str, show_power: bool = True) -> None:

        x = [None]*5
        x[0] = (2*xb0)*BW + (BW if gate0 in 'E' else -BW if gate0 in 'W' else 0)/2
        x[1] = x[0] + (BW if gate0 in 'E' else -BW if gate0 in 'W' else 0)/2
        x[4] = (2*xb1)*BW + (BW if gate1 in 'E' else -BW if gate1 in 'W' else 0)/2
        x[3] = x[4] + (BW if gate1 in 'E' else -BW if gate1 in 'W' else 0)/2
        x[2] = (x[1] + x[3])/2

        y = [None]*5
        y[0] = (2*yb0)*BH + (BH if gate0 in 'N' else -BH if gate0 in 'S' else 0)/2
        y[1] = y[0] + (BH if gate0 in 'N' else -BH if gate0 in 'S' else 0)/2
        y[4] = (2*yb1)*BH + (BH if gate1 in 'N' else -BH if gate1 in 'S' else 0)/2
        y[3] = y[4] + (BH if gate1 in 'N' else -BH if gate1 in 'S' else 0)/2
        y[2] = (y[1] + y[3])/2

        lwidth = (2*np.log10(abs(power))+1) if abs(power)>0 else 0
        ax.plot(x, y, color=color, lw=lwidth, alpha=0.3)

        if show_power:
            ha, va = 'center', 'center' #if gate0 in "SN" and gate1 in "SN" else 'bottom'
            ltext = f'{power:.0f}W' if abs(power)>0 else ''
            ax.annotate(ltext, ((x[1]+x[3])/2, (y[2]+y[3])/2), color='black',
                    weight='bold', fontsize=9, ha=ha, va=va, alpha=0.9)
                

    def _add_box_to_ax(ax: Any, xb: int, yb: int, text: str, color: str) -> None:
        x, y = (2*xb)*BW-BW/2, (2*yb)*BH-BH/2
        r = mpatches.Rectangle((x, y), BW, BH, facecolor=color,edgecolor='black',alpha=0.3)
        ax.add_patch(r)
        cx = x + r.get_width()/2.0
        cy = y + r.get_height()/2.0
        ax.annotate(text, (cx, cy), color='black', fontsize=9, ha='center', va='center')
        
    panel_1 = (0,  1)
    solix_mppt = (0,0)        
    panel_2 = (0, -1)
    solix_split = (1,0)        
    solix_bat = (1.5, 0.75)
    solix_out = (2, 0)
    inv_mppt_1 = (3,0.75)
    inv_mppt_2 = (3,-0.75)
    inv_out = (3,0)
    plugh = (3,0)
    house = (4,0)
    grid = (4, 1)
    sinks = (4, -1)
    plug1 = (5.25 ,1)
    plug2 = (5.5 ,0.33)
    plug3 = (5.5 ,-0.33)
    plug4 = (5.25 ,-1)
        
    _add_box_to_ax(ax, *panel_1, 'PANEL1', 'orange')
    _add_box_to_ax(ax, *panel_2, 'PANEL2', 'orange')
    _add_box_to_ax(ax, *solix_mppt, 'MPPT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_split, 'SPLIT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_out, 'OUT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *solix_bat, 'BAT\nSOLIX', 'grey')
    _add_box_to_ax(ax, *house, 'METER\nHOUSE',
                   'blue' if smp>0 else 'magenta' if sbpb>0 else 'white')
    _add_box_to_ax(ax, *grid, 'POWER\nGRID',
                   'blue' if smp>0 else 'white')
    _add_box_to_ax(ax, *inv_mppt_1, 'MPPT1\nINV', 'cyan')
    _add_box_to_ax(ax, *inv_mppt_2, 'MPPT2\nINV', 'cyan')
    if spph>1:
        _add_box_to_ax(ax, *plugh, 'PLUG0\nBALCONY', 'brown')
    else:
        _add_box_to_ax(ax, *inv_out, 'OUT\nINV', 'cyan')
    _add_box_to_ax(ax, *sinks, 'MANY\nSINK', 'white')
    _add_box_to_ax(ax, *plug1, 'PLUG1\nSINK', 'white')
    _add_box_to_ax(ax, *plug2, 'PLUG2\nSINK', 'white')
    _add_box_to_ax(ax, *plug3, 'PLUG3\nSINK', 'white')
    _add_box_to_ax(ax, *plug4, 'PLUG4\nSINK', 'white')
    

    if sbpi>0 :
        _add_link_to_ax(
            ax, *panel_1, 'S', *solix_mppt, 'N',
            sbpi/2, 'orange', show_power = False) # Measured only
        _add_link_to_ax(
            ax, *panel_2, 'N', *solix_mppt, 'S',
            sbpi/2, 'orange', show_power = False) # Measured only
        _add_link_to_ax(
            ax, *solix_mppt, 'E', *solix_split, 'W',
            sbpi, 'grey')

    if sbpb<0 : #Charging
        _add_link_to_ax(
            ax, *solix_split, 'N', *solix_bat, 'W', sbpb, 'm')
    
    if sbpb>0 : #Discharging
        _add_link_to_ax(ax, *solix_bat, 'E', *solix_out, 'N',
                        sbpb, 'm',
                        show_power = sbpi+sbpb>ivp1+ivp2)

    if sbpi>0:
        _add_link_to_ax(ax, *solix_split, 'S', *solix_out, 'S',
                        sbpi+sbpb, 'grey',
                        show_power = sbpi+sbpb>ivp1+ivp2)

    
    #if (sbpo>0) and (ivp1>0):
    if (sbpo>0):
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_1, 'W',
                        ivp1 if ivp1>0 else sbpo/2,
                        'c' if ivp1>0 else 'grey',
                        show_power = ivp1>0)
    elif (ivp1>0) and not ((sbpb <0) or (sbpb >0)):
        _add_link_to_ax(ax, *panel_1, 'N', *inv_mppt_1, 'N',
                        ivp1, 'c',
                        show_power = ivp1>0)
        
    _add_link_to_ax(ax, *inv_mppt_1, 'S', *plugh, 'N',
                    ivp1 if ivp1>0 else sbpo/2,
                    'c' if ivp1>0 else 'grey',
                    show_power = False)            

    #if  (sbpo >0) and  (ivp2>0):
    if (sbpo >0):
        _add_link_to_ax(ax, *solix_out, 'E', *inv_mppt_2, 'W',
                        ivp2 if ivp2>0 else sbpo/2,
                        'c' if ivp2>0 else 'grey',
                        show_power = ivp2>0)
    elif (ivp2>0) and not ((sbpb <0) or (sbpb >0)):
        _add_link_to_ax(ax, *panel_2, 'S', *inv_mppt_2, 'S',
                        ivp2, 'c',
                        show_power = ivp2>0)

    _add_link_to_ax(ax, *inv_mppt_2, 'N', *plugh, 'S',
                    ivp2 if ivp2>0 else sbpo/2,
                    'c' if ivp2>0 else 'grey',
                    show_power = False)

    
    ivp = (ivp1+ivp2)

    balconyp = spph if spph>1 else ivp if ivp > 0 else sbpo
    
    if balconyp > 0:
        _add_link_to_ax(ax, *plugh, 'E', *house, 'W',
                        balconyp, 'c' if ivp>0 else 'grey')

    _add_link_to_ax(ax, *grid, 'S', *house, 'N', smp,
                    'blue' if smp>0 else 'brown')

    sinksp = smp + balconyp-spp1-spp2-spp3-spp4
    if sinksp > 1:
        _add_link_to_ax(ax, *house, 'S', *sinks, 'N', -sinksp, 'brown')

    if spp1>1:
        _add_link_to_ax(ax, *house, 'E', *plug1, 'W', -spp1, 'brown')
    if spp2>1:
        _add_link_to_ax(ax, *house, 'E', *plug2, 'W', -spp2, 'brown')
    if spp3>1:
        _add_link_to_ax(ax, *house, 'E', *plug3, 'W', -spp3, 'brown')
    if spp4>1:
        _add_link_to_ax(ax, *house, 'E', *plug4, 'W', -spp4, 'brown')


    # last sample time (python version independent)
    dt = datetime.strptime(str(time), '%Y-%m-%dT%H:%M:%S.%f000')
    hm = dt.strftime('%H:%M') 

    title = f'# System #'
    title += f'\nLast Sample of the Day @ {hm}'
    ax.set_title(title)
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)

    logger.info(f'done')
    return base64.b64encode(buf.getbuffer()).decode('ascii')
