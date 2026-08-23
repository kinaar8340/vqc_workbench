"""Shared helpers for parametric cells."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian


def aperture_from_radius(
    x: NDArray,
    y: NDArray,
    radius: float | None,
) -> NDArray[np.float64]:
    if radius is None or radius <= 0:
        return np.ones_like(x, dtype=float)
    rho, _ = polar_from_cartesian(x, y)
    return (rho <= radius).astype(float)


class IdentityCell(ParametricCell):
    """Pass-through (unity transmission) — useful for payload round-trips."""

    kind = "identity"

    def to_phase_mask(self, grid, wavelength_nm: float):
        x, y = grid
        return np.ones_like(x, dtype=np.complex128)
