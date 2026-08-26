"""Scientific monitor frames for the ladder coils (numpy RGB, no marketing gloss)."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.simulation.lg import gaussian_beam, lg_mode_xy
from vqc_workbench.utils.grid import cartesian_grid, polar_from_cartesian

RGB = NDArray[np.uint8]


def _lerp(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, ...]:
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _lut(stops: list[tuple[float, tuple[float, float, float]]], n: int = 256) -> NDArray[np.float64]:
    t = np.linspace(0.0, 1.0, n)
    out = np.zeros((n, 3), dtype=np.float64)
    for i, u in enumerate(t):
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= u <= t1:
                s = 0.0 if t1 == t0 else (u - t0) / (t1 - t0)
                out[i] = _lerp(c0, c1, s)
                break
        else:
            out[i] = stops[-1][1]
    return out


# Dark industrial intensity (not a glossy rainbow).
_INTENSITY_LUT = _lut(
    [
        (0.00, (0.02, 0.03, 0.04)),
        (0.12, (0.04, 0.10, 0.22)),
        (0.32, (0.05, 0.28, 0.38)),
        (0.55, (0.08, 0.52, 0.36)),
        (0.78, (0.55, 0.78, 0.28)),
        (1.00, (0.92, 0.93, 0.82)),
    ]
)

# Phase: muted cyclic (lab phase camera). Enough stops to show an
# azimuthal spiral ramp; no neon HSV.
_PHASE_LUT = _lut(
    [
        (0.00, (0.14, 0.22, 0.28)),
        (0.14, (0.12, 0.40, 0.46)),
        (0.28, (0.16, 0.52, 0.38)),
        (0.42, (0.42, 0.55, 0.22)),
        (0.57, (0.62, 0.48, 0.18)),
        (0.71, (0.55, 0.28, 0.20)),
        (0.85, (0.32, 0.18, 0.30)),
        (1.00, (0.14, 0.22, 0.28)),
    ]
)


def apply_lut(z: NDArray, lut: NDArray[np.float64] | None = None) -> RGB:
    lut = _INTENSITY_LUT if lut is None else lut
    a = np.asarray(z, dtype=np.float64)
    finite = np.isfinite(a)
    a = np.where(finite, a, 0.0)
    lo, hi = float(np.min(a)), float(np.max(a))
    if hi - lo < 1e-12:
        idx = np.zeros(a.shape, dtype=np.int64)
    else:
        idx = np.clip(((a - lo) / (hi - lo) * (len(lut) - 1)).astype(np.int64), 0, len(lut) - 1)
    rgb = lut[idx]
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def intensity_rgb(field: NDArray) -> RGB:
    return apply_lut(np.abs(np.asarray(field)) ** 2, _INTENSITY_LUT)


def phase_rgb(phase: NDArray) -> RGB:
    ang = np.asarray(phase, dtype=np.float64)
    u = (ang + np.pi) / (2.0 * np.pi)
    u = np.mod(u, 1.0)
    idx = np.clip((u * (len(_PHASE_LUT) - 1)).astype(np.int64), 0, len(_PHASE_LUT) - 1)
    return np.clip(_PHASE_LUT[idx] * 255.0, 0, 255).astype(np.uint8)


def spectral_rgb(wavelength_nm: NDArray) -> NDArray[np.float64]:
    """Approximate CIE-like RGB for visible λ (scientific, not decorative)."""
    wl = np.asarray(wavelength_nm, dtype=np.float64)
    r = np.zeros_like(wl)
    g = np.zeros_like(wl)
    b = np.zeros_like(wl)
    # piecewise visible spectrum
    m = (wl >= 380) & (wl < 440)
    r[m] = -(wl[m] - 440) / (440 - 380)
    b[m] = 1.0
    m = (wl >= 440) & (wl < 490)
    g[m] = (wl[m] - 440) / (490 - 440)
    b[m] = 1.0
    m = (wl >= 490) & (wl < 510)
    g[m] = 1.0
    b[m] = -(wl[m] - 510) / (510 - 490)
    m = (wl >= 510) & (wl < 580)
    r[m] = (wl[m] - 510) / (580 - 510)
    g[m] = 1.0
    m = (wl >= 580) & (wl < 645)
    r[m] = 1.0
    g[m] = -(wl[m] - 645) / (645 - 580)
    m = (wl >= 645) & (wl <= 780)
    r[m] = 1.0
    # intensity falloff at edges
    fade = np.ones_like(wl)
    m = (wl >= 380) & (wl < 420)
    fade[m] = 0.3 + 0.7 * (wl[m] - 380) / 40.0
    m = (wl >= 700) & (wl <= 780)
    fade[m] = 0.3 + 0.7 * (780 - wl[m]) / 80.0
    fade[(wl < 380) | (wl > 780)] = 0.0
    rgb = np.stack([r, g, b], axis=-1) * fade[..., None]
    peak = float(np.max(rgb)) or 1.0
    return np.clip(rgb / peak, 0.0, 1.0)


def colorbar_strip(lut: NDArray[np.float64] | None = None, height: int = 96, width: int = 8) -> RGB:
    lut = _INTENSITY_LUT if lut is None else lut
    n = len(lut)
    col = np.clip(lut[::-1] * 255.0, 0, 255).astype(np.uint8)
    idx = np.linspace(0, n - 1, height).astype(np.int64)
    strip = np.repeat(col[idx][:, None, :], width, axis=1)
    return strip


def rainbow_collimated(n: int = 96, w0: float = 1.0, frame: float = 0.0) -> RGB:
    """Rung 1 axial: collimated pulse with spectral (wavelength) coloring."""
    x, y = cartesian_grid(n, 3.2)
    env = np.abs(gaussian_beam(x, y, w0=w0 * (1.0 + 0.04 * np.sin(frame)))) ** 2
    # slight chromatic scale: R/G/B envelopes
    r = np.abs(gaussian_beam(x, y, w0=w0 * 1.08)) ** 2
    g = np.abs(gaussian_beam(x, y, w0=w0)) ** 2
    b = np.abs(gaussian_beam(x, y, w0=w0 * 0.90)) ** 2
    stack = np.stack([r, g, b], axis=-1)
    stack = stack / (float(np.max(stack)) or 1.0)
    env_n = env / (float(np.max(env)) or 1.0)
    rgb = stack * env_n[..., None]
    # dark pedestal so it reads as a monitor, not a sticker
    rgb = 0.08 + 0.92 * rgb
    rgb[..., 0] *= 1.05
    rgb[..., 1] *= 1.10
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def pulse_streak(n: int = 96, frame: float = 0.0) -> RGB:
    """Rung 1 spatiotemporal: elongated pulse streak (x vs z / t)."""
    z = np.linspace(0.0, 1.0, n)
    x = np.linspace(-2.4, 2.4, n)
    Z, X = np.meshgrid(z, x, indexing="xy")
    z0 = 0.42 + 0.10 * np.sin(2.0 * np.pi * (frame % 1.0))
    tau = 0.22
    env = np.exp(-(X**2) / 0.28) * np.exp(-((Z - z0) ** 2) / (2.0 * tau**2))
    env += 0.18 * np.exp(-(X**2) / 0.85) * np.exp(-((Z - z0) ** 2) / (2.0 * (tau * 2.2) ** 2))
    wl = 450.0 + 280.0 * np.clip(Z, 0, 1)
    rgb = spectral_rgb(wl) * env[..., None]
    rgb = rgb / (float(np.max(rgb)) or 1.0)
    rgb = 0.04 + 0.96 * rgb
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def helical_length_view(
    ells: tuple[int, ...] = (1,),
    n: int = 96,
    pitch: float = 2.4,
    frame: float = 0.0,
    layers: int | None = None,
) -> RGB:
    """Side-on nested helical tubes (length / propagation perspective)."""
    z = np.linspace(0.0, 10.0, n)
    x = np.linspace(-3.4, 3.4, n)
    Z, X = np.meshgrid(z, x, indexing="xy")
    img = np.zeros((n, n), dtype=np.float64)
    ells = tuple(ells if layers is None else range(1, int(layers) + 1))
    phase0 = 2.0 * np.pi * (frame % 1.0)
    for k, ell in enumerate(ells):
        a = 1.0 / (1.0 + 0.22 * k)
        r0 = 0.55 + 0.72 * k
        w = 0.20 + 0.03 * k
        cx = r0 * np.cos(int(ell) * Z * (2.0 * np.pi / pitch) + phase0)
        # front wall of the helical tube
        img += a * np.exp(-((X - cx) ** 2) / (2.0 * w * w))
        # dim back wall (3-D tube, not a second noisy lattice)
        img += 0.22 * a * np.exp(-((X - 0.55 * cx) ** 2) / (2.0 * (w * 1.35) ** 2))
    return apply_lut(img, _INTENSITY_LUT)


def nested_rings(x: NDArray, y: NDArray, ells: tuple[int, ...] = (1, 2, 3), w0: float = 1.0) -> RGB:
    rho, _ = polar_from_cartesian(x, y)
    span = float(np.max(np.abs(x))) or 1.0
    # fill the monitor; Workbench grids are wider than a single w0 donut
    w_eff = max(float(w0), 0.38 * span)
    I = np.zeros_like(np.asarray(x, dtype=np.float64))
    n_e = max(1, len(ells))
    for i, ell in enumerate(ells):
        ring = np.abs(lg_mode_xy(int(ell), x, y, w0=w_eff)) ** 2
        peak = float(np.max(ring)) or 1.0
        r0 = (0.22 + 0.62 * (i + 1) / n_e) * span
        shell = np.exp(-((rho - r0) ** 2) / (2.0 * (0.055 * span) ** 2))
        I = I + (0.92**i) * (0.40 * ring / peak + 0.70 * shell)
    return apply_lut(I, _INTENSITY_LUT)


def quaternion_phase_mask(x: NDArray, y: NDArray, ell: int = 1) -> RGB:
    """Spiral phase with a weak 2φ quaternion warp — monitor phase scale."""
    _, phi = polar_from_cartesian(x, y)
    phase = int(ell) * phi + 0.35 * np.sin(2.0 * phi)
    return phase_rgb(phase)


def vortex_intensity(x: NDArray, y: NDArray, ell: int = 1, w0: float = 1.0) -> RGB:
    return intensity_rgb(lg_mode_xy(int(ell), x, y, w0=w0))


def axial_for_stage(
    stage: str,
    *,
    field: NDArray | None = None,
    phase_mask: NDArray | None = None,
    x: NDArray | None = None,
    y: NDArray | None = None,
    ell: int = 1,
    layers: int = 3,
    frame: float = 0.0,
    n: int = 96,
) -> RGB:
    if x is None or y is None:
        x, y = cartesian_grid(n, 3.2)
    if stage == "initial":
        return rainbow_collimated(n=int(x.shape[0]), frame=frame)
    if stage == "slm":
        if phase_mask is not None:
            return phase_rgb(np.angle(phase_mask))
        return quaternion_phase_mask(x, y, ell=ell)
    if stage == "helical":
        ells = tuple(range(1, max(2, int(layers)) + 1))
        return nested_rings(x, y, ells=ells)
    if stage == "detect":
        ells = tuple(range(1, max(4, int(layers) + 1) + 1))
        return nested_rings(x, y, ells=ells, w0=0.85)
    if field is not None:
        return intensity_rgb(field)
    if phase_mask is not None:
        return phase_rgb(np.angle(phase_mask))
    return rainbow_collimated(n=int(x.shape[0]), frame=frame)


def st_for_stage(
    stage: str,
    *,
    ell: int = 1,
    layers: int = 3,
    frame: float = 0.0,
    n: int = 96,
) -> RGB:
    if stage == "initial":
        return pulse_streak(n=n, frame=frame)
    if stage == "slm":
        return helical_length_view(ells=(max(1, int(ell)),), n=n, frame=frame)
    if stage == "helical":
        ells = tuple(range(1, max(2, int(layers)) + 1))
        return helical_length_view(ells=ells, n=n, frame=frame, pitch=2.2)
    if stage == "detect":
        ells = tuple(range(1, max(4, int(layers) + 1) + 1))
        return helical_length_view(ells=ells, n=n, frame=frame, pitch=1.8)
    return pulse_streak(n=n, frame=frame)


def panel_meta(monitor_title: str, scale: str, frame_ids: list[int]) -> dict[str, Any]:
    if frame_ids:
        lo, hi = min(frame_ids), max(frame_ids)
        label = f"FR {lo}" if lo == hi else f"FR {lo}–{hi}"
    else:
        label = ""
    return {"title": monitor_title, "scale": scale, "frame_label": label}
