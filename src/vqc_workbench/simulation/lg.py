"""Laguerre–Gaussian modes and OAM projection (p=0 donut basis).

Matches the SciPy path in oam_flux.vqc_photonics and vqc_proto lg_modes.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.special import factorial, genlaguerre

from vqc_workbench.utils.grid import polar_from_cartesian


def lg_radial(p: int, ell: int, rho: NDArray, w0: float) -> NDArray[np.float64]:
    L = abs(int(ell))
    p = int(p)
    norm = np.sqrt(2.0 * factorial(L) / (np.pi * w0**2 * factorial(p)))
    rw = np.sqrt(2.0) * rho / w0
    lag = genlaguerre(p, L)(rw**2)
    radial = norm * (rw**L) * np.exp(-(rw**2) / 2.0) * lag
    return np.nan_to_num(radial, nan=0.0, posinf=0.0, neginf=0.0)


def lg_mode(
    ell: int,
    rho: NDArray,
    phi: NDArray,
    w0: float = 1.0,
    p: int = 0,
) -> NDArray[np.complex128]:
    return lg_radial(p, ell, rho, w0) * np.exp(1j * ell * phi)


def lg_mode_xy(
    ell: int,
    x: NDArray,
    y: NDArray,
    w0: float = 1.0,
    p: int = 0,
) -> NDArray[np.complex128]:
    rho, phi = polar_from_cartesian(x, y)
    return lg_mode(ell, rho, phi, w0=w0, p=p)


def project_oam_spectrum(
    field: NDArray,
    x: NDArray,
    y: NDArray,
    L_max: int,
    w0: float = 1.0,
    p: int = 0,
) -> dict[int, complex]:
    """Inner-product projection onto LG_{p,ℓ} for ℓ ∈ [-L_max, L_max]."""
    rho, phi = polar_from_cartesian(x, y)
    dx = float(x[0, 1] - x[0, 0]) if x.shape[1] > 1 else 1.0
    dy = float(y[1, 0] - y[0, 0]) if y.shape[0] > 1 else 1.0
    weights: dict[int, complex] = {}
    for ell in range(-int(L_max), int(L_max) + 1):
        basis = lg_mode(ell, rho, phi, w0=w0, p=p)
        integrand = field * np.conj(basis)
        weights[ell] = complex(np.sum(integrand) * dx * dy)
    return weights


def gaussian_beam(x: NDArray, y: NDArray, w0: float = 1.0) -> NDArray[np.complex128]:
    rho2 = np.asarray(x, dtype=float) ** 2 + np.asarray(y, dtype=float) ** 2
    return np.exp(-rho2 / w0**2).astype(np.complex128)


def helical_mode(
    ell: int,
    x: NDArray,
    y: NDArray,
    w0: float = 1.0,
) -> NDArray[np.complex128]:
    """Gaussian envelope × exp(i ℓ φ) — orthonormal-enough OAM carrier for the codec."""
    rho, phi = polar_from_cartesian(x, y)
    return np.exp(-(rho**2) / w0**2) * np.exp(1j * int(ell) * phi)


def project_helical_spectrum(
    field: NDArray,
    x: NDArray,
    y: NDArray,
    L_max: int,
    w0: float = 1.0,
) -> dict[int, complex]:
    dx = float(x[0, 1] - x[0, 0]) if x.shape[1] > 1 else 1.0
    dy = float(y[1, 0] - y[0, 0]) if y.shape[0] > 1 else 1.0
    weights: dict[int, complex] = {}
    for ell in range(-int(L_max), int(L_max) + 1):
        basis = helical_mode(ell, x, y, w0=w0)
        weights[ell] = complex(np.sum(field * np.conj(basis)) * dx * dy)
    return weights


def synthesize_helical(
    weights: dict[int, complex],
    x: NDArray,
    y: NDArray,
    w0: float = 1.0,
) -> NDArray[np.complex128]:
    field = np.zeros_like(x, dtype=np.complex128)
    for ell, c in weights.items():
        if abs(c) == 0:
            continue
        field += c * helical_mode(int(ell), x, y, w0=w0)
    return field


def synthesize_from_weights(
    weights: dict[int, complex],
    x: NDArray,
    y: NDArray,
    w0: float = 1.0,
) -> NDArray[np.complex128]:
    field = np.zeros_like(x, dtype=np.complex128)
    for ell, c in weights.items():
        if abs(c) == 0:
            continue
        field += c * lg_mode_xy(int(ell), x, y, w0=w0)
    return field
