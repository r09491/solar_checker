import sys

import numpy as np

if sys.version_info >= (3, 9):
    from typing import Any
    from numpy.typing import NDArray # mypy Crash!"

    f64 = np.float64
    f64s = NDArray[f64]

    t64 = np.datetime64
    t64s = NDArray[t64]

    strings = list[str]
    timeslots = list[str] 
else:
    from typing import Any, List, Optional, Dict

    f64 = np.float64
    f64s = np.array

    t64 = np.datetime64
    t64s = np.array

    strings = List[str] 
    timeslots = List[str] 
