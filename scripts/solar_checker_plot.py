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

import io
import base64

from matplotlib import pyplot as plt
import matplotlib.image as mpimg

#import warnings
#warnings.simplefilter("ignore")

from dataclasses import dataclass

from utils.types import f64, f64s, t64, t64s, strings, timeslots
from utils.samples import get_columns_from_csv
from utils.plots import get_w_image, get_wh_image


import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


def check_powers(price: f64) -> int:

    # Read from stdin
    c = get_columns_from_csv()
    if c is None:
        return 1
    
    time, spp = c['TIME'], c['SPP']
    
    sme, ive1, ive2 = c['SME'], c['IVE1'], c['IVE2']
    wh = get_wh_image(time, sme, ive1, ive2, spp, price)
    wh = base64.b64decode(wh)
    wh = io.BytesIO(wh)
    wh = mpimg.imread(wh, format='png')

    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']
    w = get_w_image(time, smp, ivp1, ivp2, spp)
    w = base64.b64decode(w)
    w = io.BytesIO(w)
    w = mpimg.imread(w, format='png')

    fig, axes = plt.subplots(nrows = 2, figsize = (16,14))

    text = f'Solar Checker'
    fig.text(0.5, 0.0, text, ha='center', fontsize='x-large')
    fig.tight_layout(pad=2.0)
    
    axes[0].imshow(w, interpolation='nearest')
    axes[0].axis('off')
    axes[1].imshow(wh, interpolation='nearest')
    axes[1].axis('off')

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
        err = check_powers(args.price)
    except KeyboardInterrupt:
        pass
    except TypeError:
        """If there is no stream"""
        pass
    
    return err

if __name__ == '__main__':
    sys.exit(main())
