#!/usr/bin/env python3

__doc__="""
Checks the solar power input of micro APsystems inverters against the
consumption measured by a Tasmota smartmeter in a houshold. The
APsystems inverters are to be operated in direct local mode.

Checks the input of APsystems inverters to an Antella smartplug
against the consumption measured by a Tasmota smartmeter in a
houshold. The plug may be present or absent.  If present has priority
over APsystems measuremnents.

Plots the power output in logarithmic scale to emphasise lower values
and the energy in linear scale.

Plots the power output means for defined time slots to help in
scheduling of battery outputs if they can.
"""
__version__ = "0.0.3"
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import io
import base64

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

#import warnings
#warnings.simplefilter("ignore")

from dataclasses import dataclass

from typing import Any
from utils.types import f64, f64s, t64, t64s, strings, timeslots
from utils.samples import get_columns_from_csv
from utils.plots import get_w_image, get_wh_image, XSIZE, YSIZE


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def get_w (
        time: t64s, smp: f64s,
        ivp1: f64s, ivp2: f64s, spp: f64s) -> Any:
    w = await get_w_image(time, smp, ivp1, ivp2, spp)
    logger.info('Decoding power image')
    w = base64.b64decode(w)
    w = io.BytesIO(w)
    w = mpimg.imread(w, format='png')
    logger.info('Decoded power image')
    return w


async def get_wh (
        time: t64s, sme: f64s,
        ive1: f64s, ive2: f64s,
        spp: f64s, price: f64) -> Any:
    wh = await get_wh_image(time, sme, ive1, ive2, spp, price)
    logger.info('Decoding energy image')
    wh = base64.b64decode(wh)
    wh = io.BytesIO(wh)
    wh = mpimg.imread(wh, format='png')
    logger.info('Decoded energy image')
    return wh

async def get_images(c: dict, price: f64) -> Any:

    time, spp = c['TIME'], c['SPP']
    sme, ive1, ive2 = c['SME'], c['IVE1'], c['IVE2']
    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']

    results = await asyncio.gather(
        get_w(time, smp, ivp1, ivp2, spp),
        get_wh(time, sme, ive1, ive2, spp, price),
    )

    return results


async def check_powers(price: f64) -> int:
    # Read from stdin
    c = await get_columns_from_csv()
    if c is None:
        logger.error(f'No power input data available')
        return 1

    w, wh = await get_images(c, price)

    logger.info('Plotting started')

    fig, axes = plt.subplots(
        nrows = 2, sharex = True, figsize = (2*XSIZE,4*YSIZE))

    text = f'Solar Checker'
    fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')
    fig.tight_layout(pad=2.0)

    axes[0].clear()
    axes[0].imshow(w)
    axes[0].set_axis_off()

    axes[1].clear()
    axes[1].imshow(wh)
    axes[1].set_axis_off()

    logger.info('Plotting done')

    plt.show()

    return 0


@dataclass
class Script_Arguments:
    price: f64

def parse_arguments() -> Script_Arguments:

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Check solar power input',
        epilog=__doc__)
        
    parser.add_argument('--version',
                        action = 'version', version = __version__)

    parser.add_argument('--price', type = f64, default = 0.369,
                        help = "The price of energy per kWh")

    args = parser.parse_args()
    return Script_Arguments(args.price)


def main() -> int:
    args = parse_arguments()

    err = 0
    
    try:
        err = asyncio.run(check_powers(args.price))
    except KeyboardInterrupt:
        pass
    except TypeError:
        """If there is no stream"""
        pass
    
    return err

if __name__ == '__main__':
    sys.exit(main())
