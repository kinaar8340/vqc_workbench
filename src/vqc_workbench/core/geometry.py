"""Thin wrappers over flux_hopf_lib Hopf / quaternion primitives.

Falls back to local implementations when flux_hopf_lib is not installed so
the workbench remains usable as a standalone research prototype.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

try:
    from flux_hopf_lib.quaternion import encode_shard as lib_encode_shard

    _HAS_LIB = True
except Exception:  # pragma: no cover - optional
    lib_encode_shard = None
    _HAS_LIB = False


@dataclass
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_array(self) -> NDArray[np.float64]:
        return np.array([self.w, self.x, self.y, self.z], dtype=np.float64)

    def norm(self) -> float:
        return float(np.linalg.norm(self.as_array()))

    def normalize(self) -> Quaternion:
        n = self.norm()
        if n < 1e-12:
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        a = self.as_array() / n
        return Quaternion(float(a[0]), float(a[1]), float(a[2]), float(a[3]))

    def chordal_distance(self, other: Quaternion) -> float:
        a, b = self.as_array(), other.as_array()
        return float(min(np.linalg.norm(a - b), np.linalg.norm(a + b)))

    @classmethod
    def from_array(cls, arr: NDArray | list[float]) -> Quaternion:
        a = np.asarray(arr, dtype=float).reshape(-1)
        if a.size < 4:
            a = np.pad(a, (0, 4 - a.size))
        return cls(float(a[0]), float(a[1]), float(a[2]), float(a[3]))


def hopf_map(q: Quaternion) -> NDArray[np.float64]:
    """Classical Hopf projection S³ → S² from q = w + xi + yj + zk."""
    w, x, y, z = q.w, q.x, q.y, q.z
    y1 = w**2 + x**2 - y**2 - z**2
    y2 = 2.0 * (w * z + x * y)
    y3 = 2.0 * (x * z - w * y)
    vec = np.array([y1, y2, y3], dtype=np.float64)
    n = np.linalg.norm(vec)
    return vec / n if n > 1e-12 else vec


def encode_shard(payload: bytes | NDArray) -> Quaternion:
    if _HAS_LIB and lib_encode_shard is not None:
        q = lib_encode_shard(payload)
        return Quaternion(q.w, q.x, q.y, q.z)
    if isinstance(payload, (bytes, bytearray)):
        arr = np.frombuffer(bytes(payload)[:16].ljust(16, b"\x00"), dtype=np.uint8).astype(float)
    else:
        arr = np.asarray(payload, dtype=float).flatten()
    if arr.size < 4:
        arr = np.pad(arr, (0, 4 - arr.size))
    arr = arr[:4] - np.mean(arr[:4])
    n = np.linalg.norm(arr)
    if n < 1e-12:
        return Quaternion(1.0, 0.0, 0.0, 0.0)
    arr = arr / n
    return Quaternion(float(arr[0]), float(arr[1]), float(arr[2]), float(arr[3]))


def flux_hopf_available() -> bool:
    return _HAS_LIB
