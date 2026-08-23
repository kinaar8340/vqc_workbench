"""Diffraction gratings, forked holograms, and spiral phase plates."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.structures.base import aperture_from_radius
from vqc_workbench.utils.grid import polar_from_cartesian


@register("spiral_phase")
class SpiralPhasePlate(ParametricCell):
    """Helical phase mask exp(i ℓ φ) — seeds an LG_{p,ℓ} beam."""

    kind = "spiral_phase"

    def __init__(self, name: str = "spiral_phase", params=None, material=None):
        params = dict(params or {})
        params.setdefault("ell", 1)
        params.setdefault("radius_mm", 5.0)
        params.setdefault("p", 0)
        super().__init__(name=name or f"spiral_ell{params['ell']}", params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        _, phi = polar_from_cartesian(x, y)
        ell = int(self.params.get("ell", 1))
        radius = self.params.get("radius")
        mask = np.exp(1j * ell * phi)
        return mask * aperture_from_radius(x, y, radius)


@register("binary_grating")
class BinaryGrating(ParametricCell):
    """1D binary phase grating (thin-element)."""

    kind = "binary_grating"

    def __init__(self, name: str = "binary_grating", params=None, material=None):
        params = dict(params or {})
        params.setdefault("period", 0.4)
        params.setdefault("duty", 0.5)
        params.setdefault("depth_rad", np.pi)
        params.setdefault("angle_deg", 0.0)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        period = float(self.params["period"])
        duty = float(self.params["duty"])
        depth = float(self.params["depth_rad"])
        angle = np.deg2rad(float(self.params["angle_deg"]))
        u = x * np.cos(angle) + y * np.sin(angle)
        frac = np.mod(u / period, 1.0)
        phase = np.where(frac < duty, depth, 0.0)
        return np.exp(1j * phase)


@register("blazed_grating")
class BlazedGrating(ParametricCell):
    """Sawtooth phase grating."""

    kind = "blazed_grating"

    def __init__(self, name: str = "blazed_grating", params=None, material=None):
        params = dict(params or {})
        params.setdefault("period", 0.5)
        params.setdefault("depth_rad", 2 * np.pi)
        params.setdefault("angle_deg", 0.0)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        period = float(self.params["period"])
        depth = float(self.params["depth_rad"])
        angle = np.deg2rad(float(self.params["angle_deg"]))
        u = x * np.cos(angle) + y * np.sin(angle)
        frac = np.mod(u / period, 1.0)
        return np.exp(1j * depth * frac)


@register("forked_hologram")
class ForkedHologram(ParametricCell):
    """Forked grating: spiral phase + linear carrier (classic LG hologram)."""

    kind = "forked_hologram"

    def __init__(self, name: str = "forked_hologram", params=None, material=None):
        params = dict(params or {})
        params.setdefault("ell", 1)
        params.setdefault("period", 0.35)
        params.setdefault("angle_deg", 0.0)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        _, phi = polar_from_cartesian(x, y)
        ell = int(self.params["ell"])
        period = float(self.params["period"])
        angle = np.deg2rad(float(self.params["angle_deg"]))
        u = x * np.cos(angle) + y * np.sin(angle)
        carrier = 2.0 * np.pi * u / period
        return np.exp(1j * (ell * phi + carrier))
