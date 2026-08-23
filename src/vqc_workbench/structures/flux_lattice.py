"""Hopf-lattice defect / flywheel cells (oam_flux / hfb inspired)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian


@register("flux_lattice")
class FluxLatticeDefect(ParametricCell):
    """Ring of vortices on a gauged Hopf lattice (thin-element analog)."""

    kind = "flux_lattice"

    def __init__(self, name: str = "flux_lattice", params=None, material=None):
        params = dict(params or {})
        params.setdefault("ell", 3)
        params.setdefault("n_sites", 8)
        params.setdefault("ring_radius", 1.2)
        params.setdefault("kappa", 0.85)
        params.setdefault("core_sigma", 0.25)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        ell = int(self.params["ell"])
        n_sites = int(self.params["n_sites"])
        ring = float(self.params["ring_radius"])
        kappa = float(self.params["kappa"])
        sigma = float(self.params["core_sigma"])
        field = np.ones_like(x, dtype=np.complex128)
        for k in range(n_sites):
            theta = 2.0 * np.pi * k / n_sites
            x0 = ring * np.cos(theta)
            y0 = ring * np.sin(theta)
            dx, dy = x - x0, y - y0
            phi_k = np.arctan2(dy, dx)
            amp = np.exp(-(dx**2 + dy**2) / (2.0 * sigma**2))
            winding = ell if k % 2 == 0 else -ell
            field *= np.exp(1j * winding * phi_k * kappa * amp)
        rho, phi = polar_from_cartesian(x, y)
        # Global helical carrier (nested helix).
        field *= np.exp(1j * ell * phi) * np.exp(-(rho**2) / (2.0 * (ring * 1.8) ** 2))
        amp = np.abs(field)
        peak = float(np.max(amp)) or 1.0
        return (amp / peak) * np.exp(1j * np.angle(field))
