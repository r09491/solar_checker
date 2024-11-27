#!/usr/bin/env python3

__doc__=""" Saves the powerplots to png images
"""
__version__ = "0.1."
__author__ = "r09491@gmail.com"

import os
import sys
import argparse
import asyncio

import io
import base64
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

#import warnings
#warnings.simplefilter("ignore")

from dataclasses import dataclass

from typing import Any
from utils.types import f64, f64s, t64, t64s, strings, timeslots
from utils.samples import get_columns_from_csv
from utils.plots import get_blocks, get_w_line, get_kwh_line, XSIZE, YSIZE


import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s',
    datefmt='%H:%M:%S',)
logger = logging.getLogger(os.path.basename(sys.argv[0]))


async def get_blocks_png(time: t64, smp: f64,
                     ivp1: f64, ivp2: f64, spph: f64,
                     sbpi: f64s, sbpo: f64s, sbpb: f64,
                     spp1: f64, spp2: f64, spp3: f64, spp4: f64):
    logger.info('Decoding blocks image')
    bytes = io.BytesIO(base64.b64decode(await get_blocks(**vars())))
    blocks_png = mpimg.imread(bytes, format='png')
    logger.info('Decoded blocks image')
    return blocks_png


async def get_w_png (
        time: t64s, smp: f64s,
        ivp1: f64s, ivp2: f64s, spph: f64s,
        sbpi: f64s, sbpo: f64s, sbpb: f64s) -> Any:
    logger.info('Decoding power image')
    bytes = io.BytesIO(base64.b64decode(await get_w_line(**vars())))
    w_png = mpimg.imread(bytes, format='png')
    logger.info('Decoded power image')
    return w_png


async def get_kwh_png (
        time: t64s, smeon: f64s, smeoff: f64s,
        ive1: f64s, ive2: f64s, speh: f64s, sbei: f64s, sbeo: f64s,
        sbebcharge: f64s, sbebdischarge: f64s, sbsb: f64s,
        empty_kwh, full_kwh: f64s, price: f64) -> Any:
    logger.info('Decoding energy image')
    bytes = io.BytesIO(base64.b64decode(await get_kwh_line(**vars())))
    wh_png = mpimg.imread(bytes, format='png')
    logger.info('Decoded energy image')
    return wh_png


async def get_images(c: dict, empty_kwh:f64, full_kwh:f64, price: f64) -> Any:
    logger.info(f'get_images started')

    time, spph = c['TIME'], c['SPPH']
    ##sme, ive1, ive2 = c['SME'], c['IVE1'], c['IVE2']
    smp, ivp1, ivp2 = c['SMP'], c['IVP1'], c['IVP2']
    sbpi, sbpo, sbpb, sbsb = c['SBPI'], c['SBPO'], c['SBPB'], c['SBSB']
    spp1, spp2, spp3, spp4 = c['SPP1'], c['SPP2'], c['SPP3'], c['SPP4']

    smpon = np.zeros_like(smp)
    smpon[smp>0] = smp[smp>0]
    smpoff = np.zeros_like(smp)
    smpoff[smp<=0] = -smp[smp<=0]

    sbpbcharge = np.zeros_like(sbpb)
    sbpbcharge[sbpb<0] = -sbpb[sbpb<0]
    sbpbdischarge = np.zeros_like(sbpb)
    sbpbdischarge[sbpb>0] = sbpb[sbpb>0]
    
    blocks_png, w_png, kwh_png = await asyncio.gather(
        get_blocks_png(time[-1], smp[-1], ivp1[-1], ivp2[-1],
                       spph[-1] if spph is not None else 0,
                       sbpi[-1] if sbpi is not None else 0,
                       sbpo[-1] if sbpo is not None else 0,
                       sbpb[-1] if sbpb is not None else 0,
                       spp1[-1] if spp1 is not None else 0,
                       spp2[-1] if spp2 is not None else 0,
                       spp3[-1] if spp3 is not None else 0,
                       spp4[-1] if spp4 is not None else 0),
        get_w_png(time, smp, ivp1, ivp2,
                   spph, sbpi, sbpo, sbpb),
        get_kwh_png(time,
            smpon.cumsum()/1000/60 if smpon is not None else None,
            smpoff.cumsum()/1000/60 if smpoff is not None else None,
            ivp1.cumsum()/1000/60 if ivp1 is not None else None,
            ivp2.cumsum()/1000/60 if ivp2 is not None else None,
            spph.cumsum()/1000/60 if spph is not None else None,
            sbpi.cumsum()/1000/60 if sbpi is not None else None,
            sbpo.cumsum()/1000/60 if sbpo is not None else None,
            sbpbcharge.cumsum()/1000/60 if sbpb is not None else None,
            sbpbdischarge.cumsum()/1000/60 if sbpb is not None else None,
            sbsb*full_kwh if sbsb is not None else None,
                     empty_kwh, full_kwh, price))
    logger.info(f'get_images done')
    return blocks_png, w_png, kwh_png


async def save_powers(logday: str,
                      logprefix: str,
                      logdir: str,
                      outdir: str,
                      empty_kwh:f64,
                      full_kwh:f64,
                      price: f64) -> int:

    if (outdir is None) or (not os.path.isdir(outdir)):
        logger.error(f'"{outdir}" is not a directory')
        return 11

    if (logdir is None) or (not os.path.isdir(logdir)):
        logger.error(f'"{logdir}" is not a directory')
        return 12

    if (logday is None):
        logger.error(f'"{logday}" is not a logday')
        return 13

    if (logprefix is None):
        logger.error(f'"{logprefix}" is not a logprefix')
        return 14
        
    logfile = os.path.join(logdir, f'{logprefix}_{logday}.log' )
    if not os.path.isfile(logfile):
        logger.error(f'"{logfile}" is not a file')
        return 15
    

    # Read from stdin
    c = await get_columns_from_csv(logday, logprefix, logdir)
    if c is None:
        logger.error(f'No power input data available')
        return 1

    blocks, w, kwh = await get_images(c, empty_kwh, full_kwh,price)

    logger.info('Save started')
    
    mpimg.imsave(os.path.join(outdir, f'blocks_{logday}.png'), blocks)
    mpimg.imsave(os.path.join(outdir, f'power_{logday}.png'), w)
    mpimg.imsave(os.path.join(outdir, f'energy_{logday}.png'), kwh)

    logger.info(f'Save done to directory "{outdir}"')
    return 0


@dataclass
class Script_Arguments:
    logday: str
    logprefix:str
    logdir:str
    outdir: str
    empty_kwh: f64
    full_kwh: f64
    price: f64

def parse_arguments() -> Script_Arguments:

    parser = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        description='Save solar power diagrams',
        epilog=__doc__)
        
    parser.add_argument('--version',
                        action = 'version', version = __version__)

    parser.add_argument('--logday', type = str, required = True,
                        help = "day for forecast 'ymd'")

    parser.add_argument('--logprefix', type = str, required = True,
                        help = "Prefix of the record file'")

    parser.add_argument('--logdir', type = str, required = True,
                        help = "Directory of the record files'")

    parser.add_argument('--outdir', type = str, required = True,
                        help = "The output directory for the images")
    
    parser.add_argument('--empty_kwh', type = f64, default = 0.160,
                        help = "The battery empty kWh")

    parser.add_argument('--full_kwh', type = f64, default = 1.600,
                        help = "The battery full kWh")

    parser.add_argument('--price', type = f64, default = 0.369,
                        help = "The price of energy per kWh")

    args = parser.parse_args()
    return Script_Arguments(
        args.logday,
        args.logprefix,
        args.logdir,
        args.outdir,
        args.empty_kwh,
        args.full_kwh,
        args.price
    )


def main() -> int:
    args = parse_arguments()

    err = 0


    try:
        err = asyncio.run(
            save_powers(
                args.logday,
                args.logprefix,
                args.logdir,
                args.outdir,
                args.empty_kwh,
                args.full_kwh,
                args.price
            )
        )


    except KeyboardInterrupt:
        pass
    except TypeError:
        pass
    
    return err

if __name__ == '__main__':
    sys.exit(main())
