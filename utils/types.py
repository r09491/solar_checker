import sys

import numpy as np

if sys.version_info >= (3, 9): 
    from numpy.typing import NDArray # mypy Crash!"

    f64 = np.float64
    f64s = NDArray[f64]

    t64 = np.datetime64
    t64s = NDArray[t64]

    strings = list[str]
    timeslots = list[str] 
else:
    from typing import Any, List

    f64 = np.float64
    f64s = Any

    t64 = np.datetime64
    t64s = Any

    strings = List[str] 
    timeslots = List[str] 
