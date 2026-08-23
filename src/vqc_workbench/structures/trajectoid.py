"""Trajectoid-style shells with phase-mask trenches.

Analytic fallback always works. When ``flux_trajectoid`` is installed the
``to_geometry_dict`` path can attach a live ``ShellGeometry`` fingerprint.
"""

from __future__ import annotations

import hashlib

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian


def _hash_seed(payload_hash: str | None) -> int:
    raw = (payload_hash or "vqc").encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


@register("trajectoid")
class TrajectoidShell(ParametricCell):
    """Rolling-path trench mask: azimuthal winding + radial Fourier ripples."""

    kind = "trajectoid"

    def __init__(self, name: str = "trajectoid", params=None, material=None):
        params = dict(params or {})
        params.setdefault("payload_hash", None)
        params.setdefault("n_trenches", 8)
        params.setdefault("winding", 2)
        params.setdefault("trench_depth_rad", np.pi)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        rho, phi = polar_from_cartesian(x, y)
        n = int(self.params["n_trenches"])
        winding = int(self.params["winding"])
        depth = float(self.params["trench_depth_rad"])
        rng = np.random.default_rng(_hash_seed(self.params.get("payload_hash")))
        # Deterministic Fourier ripple of the rolling path, encoded as phase trenches.
        k = 2.0 + 0.15 * rng.standard_normal()
        trench = np.cos(n * phi + winding * np.log1p(rho) * k)
        phase = depth * 0.5 * (1.0 + trench)
        helical = winding * phi
        return np.exp(1j * (phase + helical))

    def to_geometry_dict(self):
        spec = super().to_geometry_dict()
        try:
            from flux_trajectoid import generate_shell  # type: ignore

            spec["live_shell"] = True
            spec["generator"] = "flux_trajectoid.generate_shell"
        except Exception:
            spec["live_shell"] = False
        return spec
