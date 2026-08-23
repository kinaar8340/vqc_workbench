"""User-defined structure from a dict, YAML, or callable."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.structures.base import IdentityCell
from vqc_workbench.utils.grid import polar_from_cartesian


@register("identity")
class IdentityStructure(IdentityCell):
    kind = "identity"


@register("custom")
class CustomStructure(ParametricCell):
    """Pass a ``phase_func(x, y, wavelength_nm)`` or a stored complex mask."""

    kind = "custom"

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        fn = self.params.get("phase_func")
        mask = self.params.get("mask")
        if callable(fn):
            phase = np.asarray(fn(x, y, wavelength_nm), dtype=float)
            return np.exp(1j * phase)
        if mask is not None:
            arr = np.asarray(mask)
            if arr.shape != x.shape:
                raise ValueError(f"custom mask shape {arr.shape} != grid {x.shape}")
            return arr.astype(np.complex128)
        # default: weak helical so it is not a silent no-op
        _, phi = polar_from_cartesian(x, y)
        ell = int(self.params.get("ell", 0))
        return np.exp(1j * ell * phi)
