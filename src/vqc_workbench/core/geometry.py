"""Re-exports of flux_hopf_lib Hopf / quaternion primitives.

Quaternion algebra and the classical Hopf map live in flux_hopf_lib.
This module keeps the workbench call shape (Quaternion in, ndarray out).
Do not fork the map here.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from flux_hopf_lib.hopf import hopf_map_quaternion
from flux_hopf_lib.quaternion import Quaternion, encode_shard

__all__ = [
    "Quaternion",
    "encode_shard",
    "hopf_map",
    "flux_hopf_available",
]


def hopf_map(q: Quaternion) -> NDArray[np.float64]:
    """Classical Hopf projection S³ → S² from q = w + xi + yj + zk."""
    y1, y2, y3 = hopf_map_quaternion(q.w, q.x, q.y, q.z)
    return np.array([y1, y2, y3], dtype=np.float64)


def flux_hopf_available() -> bool:
    return True
