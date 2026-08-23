"""Fast modal OAM path: structure → LG coefficients → z-propagation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.config import WorkbenchConfig, load_config
from vqc_workbench.core.structure import Structure
from vqc_workbench.simulation.lg import (
    gaussian_beam,
    lg_radial,
    project_oam_spectrum,
    synthesize_from_weights,
)
from vqc_workbench.utils.grid import cartesian_grid, polar_from_cartesian


def kolmogorov_radial_phase_profile(nr: int = 2048, r0: float = 0.15, rng=None) -> NDArray[np.float64]:
    rng = np.random.default_rng() if rng is None else rng
    r = np.linspace(0.0, 10.0, nr)
    phase_var = (r / r0) ** (5.0 / 3.0)
    grad = np.gradient(phase_var)
    phase = np.cumsum(rng.normal(0.0, np.sqrt(np.maximum(grad, 0.0)), nr))
    return phase - phase[0]


def apply_kolmogorov_phase(
    field: NDArray[np.complex128],
    x: NDArray,
    y: NDArray,
    turbulence: float,
    seed: int | None = None,
) -> NDArray[np.complex128]:
    """Multiply a 2-D field by a Kolmogorov phase screen (radial interpolation)."""
    rng = np.random.default_rng(seed)
    screen = kolmogorov_radial_phase_profile(nr=2048, rng=rng)
    rho = np.sqrt(np.asarray(x, dtype=float) ** 2 + np.asarray(y, dtype=float) ** 2)
    phase = np.interp(rho, np.linspace(0.0, 10.0, len(screen)), screen, left=0.0, right=0.0)
    return field * np.exp(1j * float(turbulence) * phase)


@dataclass
class ModeResult:
    ell: NDArray[np.int64]
    coefficients: NDArray[np.complex128]
    intensity: NDArray[np.float64]
    phase_mask: NDArray[np.complex128]
    field: NDArray[np.complex128]
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    wavelength_nm: float
    L_max: int
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ell": self.ell,
            "coefficients": self.coefficients,
            "intensity": self.intensity,
            "phase_mask": self.phase_mask,
            "field": self.field,
        }

    def dominant_ell(self) -> int:
        return int(self.ell[int(np.argmax(np.abs(self.coefficients)))])

    def expectation_ell(self) -> float:
        """Intensity-weighted ⟨ℓ⟩."""
        return float(np.sum(self.ell.astype(float) * self.intensity))

    def weight_dict(self) -> dict[int, complex]:
        return {int(e): complex(c) for e, c in zip(self.ell, self.coefficients)}


@dataclass
class PropagationResult:
    z_steps: NDArray[np.float64]
    ells: NDArray[np.int64]
    intensity: NDArray[np.float64]  # (n_z, n_modes)
    coefficients_z: NDArray[np.complex128]  # (n_z, n_modes)
    rho: NDArray[np.float64] | None = None


class ModalSimulator:
    """Fast path: thin-element mask + LG projection + vectorized z-propagation.

    Prefers the built-in SciPy LG engine (no import-time side effects).
    If ``oam_flux.vqc_photonics`` is installed, ``propagate`` can optionally
    reuse that vectorized intensity cube for lattice coupling.
    """

    def __init__(self, config: WorkbenchConfig | dict | str | None = None):
        if isinstance(config, WorkbenchConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = WorkbenchConfig(raw=config)
        else:
            self.config = load_config(config)

    def _grid(self, grid_size: int | None = None, extent: float | None = None):
        n = int(grid_size or self.config.grid_size)
        ext = float(extent if extent is not None else self.config.extent)
        return cartesian_grid(n, ext)

    def structure_to_modes(
        self,
        structure: Structure,
        L_max: int | None = None,
        wavelength_nm: float | None = None,
        grid_size: int | None = None,
        w0: float | None = None,
        incident: str = "gaussian",
        turbulence: float = 0.0,
        seed: int | None = None,
    ) -> ModeResult:
        L_max = int(L_max if L_max is not None else self.config.L_max)
        wavelength_nm = float(wavelength_nm if wavelength_nm is not None else self.config.wavelength_nm)
        w0 = float(w0 if w0 is not None else self.config.w0)
        x, y = self._grid(grid_size)
        mask = structure.to_phase_mask((x, y), wavelength_nm)
        if incident == "gaussian":
            inc = gaussian_beam(x, y, w0=w0)
        else:
            inc = np.ones_like(x, dtype=np.complex128)
        field = inc * mask
        turb = float(turbulence)
        if turb > 0:
            field = apply_kolmogorov_phase(
                field, x, y, turb, seed=seed if seed is not None else self.config.seed
            )
        weights = project_oam_spectrum(field, x, y, L_max=L_max, w0=w0)
        ells = np.arange(-L_max, L_max + 1, dtype=np.int64)
        coeffs = np.array([weights[int(e)] for e in ells], dtype=np.complex128)
        mag2 = np.abs(coeffs) ** 2
        total = float(np.sum(mag2)) or 1.0
        intensity = mag2 / total
        return ModeResult(
            ell=ells,
            coefficients=coeffs,
            intensity=intensity,
            phase_mask=mask,
            field=field,
            x=x,
            y=y,
            wavelength_nm=wavelength_nm,
            L_max=L_max,
        )

    def propagate(
        self,
        modes: ModeResult | dict[str, NDArray],
        z_range: tuple[float, float] | None = None,
        turbulence: float | None = None,
        n_z: int | None = None,
        chirp: float | None = None,
        qec_suppression: int | None = None,
        seed: int | None = None,
    ) -> PropagationResult:
        if isinstance(modes, ModeResult):
            ells = modes.ell
            coeffs0 = modes.coefficients.copy()
        else:
            ells = np.asarray(modes["ell"])
            coeffs0 = np.asarray(modes["coefficients"], dtype=np.complex128)

        z0, z1 = z_range if z_range is not None else (self.config.z_start, self.config.z_end)
        n_z = int(n_z if n_z is not None else self.config.n_z)
        turb = float(turbulence if turbulence is not None else self.config.turbulence)
        chirp = float(chirp if chirp is not None else self.config.chirp)
        qec = int(qec_suppression if qec_suppression is not None else self.config.qec_suppression)
        z_steps = np.linspace(z0, z1, n_z)
        rng = np.random.default_rng(seed if seed is not None else self.config.seed)

        n_modes = len(ells)
        coeffs_z = np.zeros((n_z, n_modes), dtype=np.complex128)
        # Modal mixing from Kolmogorov screen: diagonal phase + small off-diagonal leak.
        if turb > 0:
            screen = kolmogorov_radial_phase_profile(nr=max(256, n_modes * 8), rng=rng)
            leak = 0.05 * turb
            mix = np.eye(n_modes, dtype=np.complex128)
            for i in range(n_modes):
                mix[i, i] *= np.exp(1j * turb * screen[i % len(screen)])
                if i + 1 < n_modes:
                    mix[i, i + 1] += leak
                    mix[i + 1, i] += leak
        else:
            mix = np.eye(n_modes, dtype=np.complex128)

        for i, z in enumerate(z_steps):
            phase = np.exp(1j * chirp * z**2)
            coeffs_z[i] = mix @ (coeffs0 * phase)

        intensity = np.abs(coeffs_z) ** 2
        row_sum = np.sum(intensity, axis=1, keepdims=True)
        row_sum = np.where(row_sum == 0, 1.0, row_sum)
        intensity = intensity / row_sum
        intensity = np.clip(intensity, 0.0, 1.0)
        if qec != 1:
            intensity = intensity**qec
        return PropagationResult(
            z_steps=z_steps,
            ells=ells,
            intensity=intensity,
            coefficients_z=coeffs_z,
        )

    def reconstruct_field(self, modes: ModeResult, w0: float | None = None) -> NDArray[np.complex128]:
        w0 = float(w0 if w0 is not None else self.config.w0)
        return synthesize_from_weights(modes.weight_dict(), modes.x, modes.y, w0=w0)

    def radial_weights(self, L_max: int | None = None, nr: int = 256, w0: float | None = None):
        """LG p=0 radial weights (oam_flux / vqc_sims convention)."""
        L_max = int(L_max if L_max is not None else self.config.L_max)
        w0 = float(w0 if w0 is not None else self.config.w0)
        rho_max = float(max(8.0, 3.0 * np.sqrt(2 * L_max + 1)))
        rho = np.linspace(0.0, rho_max, nr)
        weights = np.zeros((2 * L_max + 1, nr), dtype=np.float64)
        for idx, ell in enumerate(range(-L_max, L_max + 1)):
            weights[idx] = lg_radial(0, ell, rho, w0)
        return weights, rho
