"""Cartesian / polar grids for phase masks and LG projection."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.floating]


def cartesian_grid(
    n: int = 128,
    extent: float = 4.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Centered (x, y) meshgrid with half-width ``extent``."""
    axis = np.linspace(-extent, extent, int(n))
    return np.meshgrid(axis, axis, indexing="xy")


def polar_from_cartesian(
    x: Array,
    y: Array,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return (rho, phi) from Cartesian meshgrids."""
    rho = np.sqrt(np.asarray(x, dtype=float) ** 2 + np.asarray(y, dtype=float) ** 2)
    phi = np.arctan2(np.asarray(y, dtype=float), np.asarray(x, dtype=float))
    return rho, phi
