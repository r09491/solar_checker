__doc__=""" """
__version__ = "0.0.0"
__author__ = "r09491@gmail.com"

from .get_columns_from_csv import get_columns_from_csv
async def get_kwh_cumsum_from_csv(
        logday: str = None,
        logprefix: str = None,
        logdir: str = None) -> dict:
    c = await get_columns_from_csv(logday,logprefix, logdir)
    return {'SME' : c['SMP'].cumsum()/60.0/1000.0 if c and 'SMP' in c else 0.0,
            'IVE1' : c['IVP1'].cumsum()/60.0/1000.0 if c and 'IVE1' in c else 0.0,
            'IVE2' : c['IVP2'].cumsum()/60.0/1000.0 if c and 'IVE2' in c else 0.0,
            'SPEH' : c['SPPH'].cumsum()/60.0/1000.0 if c and 'SPPH' in c else 0.0,
            'SBEO' : c['SBPO'].cumsum()/60.0/1000.0 if c and 'SBPO' in c else 0.0}
