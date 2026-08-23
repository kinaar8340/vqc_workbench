"""Orbital Braille typehead — PWM-gated multi-orb snapshot as a phase mask.

Thin-wraps ``vqc_proto.orbital_braille`` when that package is importable;
otherwise synthesizes the same geometry locally (see typehead.synthesize_orb_field).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell

GOLDEN_ANGLE = np.deg2rad(137.507764)


def _local_orbs(n_orbs: int, duties: list[float] | None) -> list[dict[str, Any]]:
    duties = list(duties) if duties is not None else [0.5] * n_orbs
    orbs = []
    for k in range(n_orbs):
        duty = float(duties[k]) if k < len(duties) else 0.5
        orbs.append(
            {
                "radius": 0.4 + 0.15 * k,
                "omega": 1.0 + 0.3 * k,
                "ell": k if k % 2 == 0 else -(k // 2 + 1),
                "amplitude": 0.8 + 0.1 * k,
                "phase0": k * GOLDEN_ANGLE,
                "pwm_duty": duty,
            }
        )
    return orbs


def _synthesize_orbs(
    orbs: list[dict[str, Any]],
    x: NDArray,
    y: NDArray,
    t_val: float,
    t_max: float,
    w0: float,
) -> NDArray[np.complex128]:
    field = np.zeros_like(x, dtype=np.complex128)
    sigma = w0 * 0.35
    for orb in orbs:
        theta = orb["phase0"] + orb["omega"] * t_val
        x0 = orb["radius"] * np.cos(theta)
        y0 = orb["radius"] * np.sin(theta)
        pwm_on = (np.sin(2 * np.pi * orb["omega"] * t_val / t_max) + 1) / 2 < orb["pwm_duty"]
        gate = 1.0 if pwm_on else 0.15
        phase = orb["omega"] * t_val + orb["phase0"]
        amp = orb["amplitude"] * gate * np.exp(1j * phase)
        gauss = np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * sigma**2))
        helical = np.exp(1j * orb["ell"] * np.arctan2(y - y0, x - x0))
        field += amp * gauss * helical
    return field


@register("orbital_braille")
class OrbitalBrailleTypehead(ParametricCell):
    """Multi-orb PWM typehead frozen at ``t_frac * t_max``."""

    kind = "orbital_braille"

    def __init__(self, name: str = "orbital_braille", params=None, material=None):
        params = dict(params or {})
        params.setdefault("n_orbs", 4)
        params.setdefault("duties", [0.25, 0.5, 0.75, 0.4])
        params.setdefault("t_frac", 0.35)
        params.setdefault("t_max", 1.0)
        params.setdefault("w0", 1.0)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        n_orbs = int(self.params["n_orbs"])
        duties = list(self.params.get("duties") or [])
        t_max = float(self.params["t_max"])
        t_val = float(self.params["t_frac"]) * t_max
        w0 = float(self.params["w0"])
        orbs = _local_orbs(n_orbs, duties)
        field = _synthesize_orbs(orbs, x, y, t_val, t_max, w0)
        amp = np.abs(field)
        peak = float(np.max(amp)) or 1.0
        return (amp / peak) * np.exp(1j * np.angle(field))
