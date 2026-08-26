"""High-fidelity FR 1–16 monitor renders from Workbench structures + LG propagation."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.special import j1

from vqc_workbench.ladder.frames import (
    RGB,
    _bloom,
    _hsv_to_rgb,
    _stretch,
    _to_u8,
    apply_lut,
    phase_rgb,
    spectral_rgb,
)
from vqc_workbench.simulation.lg import gaussian_beam, lg_mode_xy, lg_radial
from vqc_workbench.utils.grid import cartesian_grid, polar_from_cartesian


def _airy(rho: NDArray, scale: float) -> NDArray[np.float64]:
    kr = np.asarray(rho, dtype=np.float64) * float(scale)
    out = np.ones_like(kr)
    m = kr > 1e-8
    u = kr[m]
    out[m] = (2.0 * j1(u) / u) ** 2
    return out


def _wb_field(kind: str, n: int, extent: float = 2.25, **params) -> tuple[NDArray, NDArray, NDArray, NDArray]:
    """Structure phase mask × Gaussian on a visual grid (Workbench structure API)."""
    from vqc_workbench.api import Workbench

    wb = Workbench()
    structure = wb.create_structure(kind, **params)
    x, y = cartesian_grid(n, extent)
    mask = structure.to_phase_mask((x, y), float(wb.config.wavelength_nm))
    field = gaussian_beam(x, y, w0=0.88) * mask
    return x, y, mask, field


def fr1_3_axial(n: int = 384) -> RGB:
    """Collimated femtosecond pulse: white core, chromatic waist, iris Airy rings."""
    x, y = cartesian_grid(n, 2.45)
    rho, _ = polar_from_cartesian(x, y)
    airy = _airy(rho, 8.2)
    rgb = np.zeros(rho.shape + (3,), dtype=np.float64)
    bands = (
        (0.20, 0.45, 1.00, 0.82),
        (0.20, 1.00, 0.38, 1.00),
        (1.00, 0.90, 0.16, 1.18),
        (1.00, 0.30, 0.10, 1.38),
    )
    for r, g, b, wsc in bands:
        env = np.exp(-(rho**2) / (0.92 * wsc) ** 2) * airy
        rgb += np.array((r, g, b)) * env[..., None]
    core = np.exp(-(rho**2) / 0.32**2)
    rgb += 1.45 * core[..., None]
    lum = np.max(rgb, axis=-1)
    rgb *= (_bloom(lum, sigma=max(0.9, n / 200.0), mix=0.24) / (lum + 1e-9))[..., None]
    rgb /= float(np.max(rgb)) or 1.0
    return _to_u8(rgb**0.86)


def fr4_5_st(ny: int = 220, nx: int = 420) -> RGB:
    """Elongated chirped pulse: Gaussian beam w(z) × temporal envelope."""
    z = np.linspace(0.0, 1.0, nx)
    x = np.linspace(-2.3, 2.3, ny)
    Z, X = np.meshgrid(z, x, indexing="xy")
    z_r = 0.55
    w0 = 0.38
    w = w0 * np.sqrt(1.0 + ((Z - 0.12) / z_r) ** 2)
    spatial = np.exp(-2.0 * X**2 / (w**2 + 1e-9))
    z0 = 0.47
    tau = 0.13
    # quadratic chirp curves the pulse front slightly
    t = (Z - z0) - 0.04 * X**2
    temporal = np.exp(-(t**2) / (2.0 * tau**2))
    temporal += 0.18 * np.exp(-((Z - (z0 - 0.20)) ** 2) / (2.0 * (tau * 0.55) ** 2)) * np.exp(-(X**2) / 0.12)
    env = _stretch(_bloom(spatial * temporal, sigma=max(0.7, nx / 280.0), mix=0.28), p=0.045)
    wl = 445.0 + 290.0 * np.clip(Z, 0.0, 1.0)
    rgb = spectral_rgb(wl) * env[..., None]
    rgb /= float(np.max(rgb)) or 1.0
    return _to_u8(rgb)


def fr6_8_axial(n: int = 384) -> RGB:
    """Vortex / quaternion spiral phase from Workbench spiral_phase ℓ=1."""
    x, y, mask, field = _wb_field("spiral_phase", n, extent=2.2, ell=1)
    _, phi = polar_from_cartesian(x, y)
    phase = np.angle(mask) + 0.32 * np.sin(2.0 * phi)
    I = _stretch(_bloom(np.abs(field) ** 2, sigma=max(0.8, n / 200.0)), p=0.05)
    rgb = phase_rgb(phase).astype(np.float64) / 255.0
    rgb *= (0.07 + 0.93 * I)[..., None]
    return _to_u8(rgb)


def _lg_helix_xz(
    ells: tuple[int, ...],
    ny: int,
    nx: int,
    *,
    w0: float = 0.62,
    z_r: float = 2.4,
    z_max: float = 10.5,
    x_span: float = 3.6,
    turns: float = 3.2,
) -> RGB:
    """x–z view of LG p=0 rings whose Poynting peak traces a Gouy-twisted helix."""
    z = np.linspace(0.05, z_max, nx)
    x = np.linspace(-x_span, x_span, ny)
    Z, X = np.meshgrid(z, x, indexing="xy")
    w = w0 * np.sqrt(1.0 + (Z / z_r) ** 2)
    gouy = np.arctan(Z / z_r)
    dens = np.zeros((ny, nx), dtype=np.float64)
    hue = np.zeros((ny, nx), dtype=np.float64)
    weight = np.zeros((ny, nx), dtype=np.float64)
    n_e = max(1, len(ells))
    rho_axis = np.linspace(0.0, x_span, 256)
    for k, ell in enumerate(ells):
        ell_i = max(1, int(abs(ell)))
        # peak radius of LG_{0,ℓ} ~ w * sqrt(|ℓ|/2)
        r_peak = w * np.sqrt(0.5 * ell_i + 0.20)
        phi_h = ell_i * gouy * (1.0 + 0.35 * ell_i) + 2.0 * np.pi * turns * (Z / z_max)
        cx = r_peak * np.cos(phi_h)
        # local radial width from the LG ring (sample 1-D radial profile)
        rad = lg_radial(0, ell_i, rho_axis, float(np.mean(w)))
        # FWHM-ish width in w0 units
        sigma = 0.28 * w * (1.0 + 0.08 * k)
        wall = np.exp(-((np.abs(X - cx) - 0.28 * sigma) ** 2) / (2.0 * (0.42 * sigma) ** 2))
        core = np.exp(-((X - cx) ** 2) / (2.0 * (0.38 * sigma) ** 2))
        back = np.exp(-((X - 0.70 * cx) ** 2) / (2.0 * (0.95 * sigma) ** 2))
        amp = (0.88**k) * (0.35 + 0.65 * (rad.max() / (rad.max() + 1e-9)))
        layer = amp * (1.05 * core + 0.38 * wall + 0.16 * back)
        dens += layer
        hk = (0.06 + 0.70 * k / max(1, n_e - 0.35) + 0.10 * (Z / z_max)) % 1.0
        hue += hk * layer
        weight += layer
    dens = _bloom(dens, sigma=max(0.55, nx / 320.0), mix=0.18)
    v = _stretch(dens, p=0.038)
    h = np.divide(hue, np.maximum(weight, 1e-9))
    return _to_u8(_hsv_to_rgb(h, 0.70 * np.ones_like(v), v))


def fr9_10_st(ny: int = 220, nx: int = 420) -> RGB:
    return _lg_helix_xz((1,), ny, nx, w0=0.70, z_r=2.6, z_max=9.5, x_span=3.2, turns=2.8)


def _nested_lg_axial(ells: tuple[int, ...], n: int, span: float = 2.2) -> RGB:
    """Concentric rings at the physical LG peak radii (Workbench LG projector)."""
    x, y = cartesian_grid(n, span)
    field = np.zeros_like(x, dtype=np.complex128)
    I = np.zeros_like(x, dtype=np.float64)
    n_e = max(1, len(ells))
    r_max = 0.40 * span
    for i, ell in enumerate(ells):
        rt = r_max * (0.22 + 0.78 * (i + 1) / n_e)
        w = rt / np.sqrt(abs(int(ell)) / 2.0 + 0.18)
        mode = lg_mode_xy(int(ell), x, y, w0=float(w))
        amp = 0.90**i
        field = field + amp * mode
        I = I + amp * np.abs(mode) ** 2
    I = _stretch(_bloom(I, sigma=max(0.6, n / 240.0), mix=0.16), p=0.04)
    base = apply_lut(I).astype(np.float64) / 255.0
    hue = np.mod((np.angle(field) + np.pi) / (2.0 * np.pi), 1.0)
    tint = _hsv_to_rgb(hue, 0.34 * I, I)
    return _to_u8(0.82 * base + 0.18 * tint)


def fr11_12_axial(n: int = 384) -> RGB:
    """Nested helical wavefronts: LG ℓ=1,2,3 at separated peak radii."""
    return _nested_lg_axial((1, 2, 3), n)


def fr13_st(ny: int = 220, nx: int = 420) -> RGB:
    return _lg_helix_xz((1, 2, 3), ny, nx, w0=0.55, z_r=2.3, z_max=10.5, x_span=3.8, turns=3.0)


def fr14_15_axial(n: int = 384) -> RGB:
    """Dense multi-layer rings: LG ℓ=1…5 at separated peak radii."""
    return _nested_lg_axial((1, 2, 3, 4, 5), n, span=2.15)


def fr16_st(ny: int = 220, nx: int = 460) -> RGB:
    return _lg_helix_xz((1, 2, 3, 4), ny, nx, w0=0.48, z_r=2.1, z_max=13.5, x_span=4.4, turns=3.6)


def prototype_monitor_images(n_ax: int = 384, n_st: tuple[int, int] = (220, 420)) -> dict[tuple[str, str], RGB]:
    ny, nx = int(n_st[0]), int(n_st[1])
    return {
        ("initial", "axial"): fr1_3_axial(n_ax),
        ("initial", "st"): fr4_5_st(ny, nx),
        ("slm", "axial"): fr6_8_axial(n_ax),
        ("slm", "st"): fr9_10_st(ny, nx),
        ("helical", "axial"): fr11_12_axial(n_ax),
        ("helical", "st"): fr13_st(ny, nx),
        ("detect", "axial"): fr14_15_axial(n_ax),
        ("detect", "st"): fr16_st(ny, nx),
    }
