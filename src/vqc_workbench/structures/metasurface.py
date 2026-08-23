"""Parameterized metasurface / phase-map cells."""

from __future__ import annotations

from typing import Callable

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian

PhaseFn = Callable[[NDArray, NDArray, float], NDArray]


@register("metasurface")
class Metasurface(ParametricCell):
    """Arbitrary phase function or sampled phase map.

    ``params['phase_func']`` may be a callable ``(x, y, wavelength_nm) -> phase_rad``
    or a 2-D array of phase (radians) resampled onto the workbench grid.
    ``params['ell_target']`` optionally adds a helical bias for OAM seeding.
    """

    kind = "metasurface"

    def __init__(self, name: str = "metasurface", params=None, material=None):
        params = dict(params or {})
        params.setdefault("ell_target", 0)
        params.setdefault("fill_factor", 1.0)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        rho, phi = polar_from_cartesian(x, y)
        ell = int(self.params.get("ell_target", 0))
        phase = ell * phi
        fn = self.params.get("phase_func")
        if callable(fn):
            phase = phase + np.asarray(fn(x, y, wavelength_nm), dtype=float)
        elif isinstance(fn, np.ndarray):
            # nearest-neighbor resample of a stored phase map
            src = np.asarray(fn, dtype=float)
            ny, nx = x.shape
            yi = np.linspace(0, src.shape[0] - 1, ny).astype(int)
            xi = np.linspace(0, src.shape[1] - 1, nx).astype(int)
            phase = phase + src[yi][:, xi]
        fill = float(self.params.get("fill_factor", 1.0))
        amp = np.where(rho <= rho.max() * np.sqrt(max(fill, 0.0)), 1.0, 0.0)
        return amp * np.exp(1j * phase)
