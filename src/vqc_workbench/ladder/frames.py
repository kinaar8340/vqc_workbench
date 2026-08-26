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


# Dark industrial intensity (luminous core on a black monitor).
_INTENSITY_LUT = _lut(
    [
        (0.00, (0.00, 0.00, 0.00)),
        (0.08, (0.02, 0.04, 0.14)),
        (0.22, (0.04, 0.16, 0.42)),
        (0.40, (0.06, 0.48, 0.52)),
        (0.58, (0.18, 0.72, 0.32)),
        (0.74, (0.78, 0.62, 0.10)),
        (0.88, (0.95, 0.82, 0.35)),
        (1.00, (0.98, 0.96, 0.92)),
    ]
)

# Cyclic phase camera (twilight ice–fire). Enough hues for a spiral ramp.
_PHASE_LUT = _lut(
    [
        (0.00, (0.08, 0.12, 0.38)),
        (0.12, (0.10, 0.42, 0.72)),
        (0.25, (0.18, 0.78, 0.72)),
        (0.40, (0.92, 0.92, 0.78)),
        (0.55, (0.92, 0.55, 0.12)),
        (0.70, (0.72, 0.16, 0.18)),
        (0.85, (0.42, 0.10, 0.42)),
        (1.00, (0.08, 0.12, 0.38)),
    ]
)

MONITOR_ASSETS: dict[tuple[str, str], str] = {
    ("initial", "axial"): "rung1_axial_fr1-3.png",
    ("initial", "st"): "rung1_st_fr4-5.png",
    ("slm", "axial"): "rung2_axial_fr6-8.png",
    ("slm", "st"): "rung2_st_fr9-10.png",
    ("helical", "axial"): "rung3_axial_fr11-12.png",
    ("helical", "st"): "rung3_st_fr13.png",
    ("detect", "axial"): "rung4_axial_fr14-15.png",
    ("detect", "st"): "rung4_st_fr16.png",
}


def _stretch(z: NDArray, p: float = 0.045) -> NDArray[np.float64]:
    """Asinh display stretch — faint structure + luminous cores."""
    a = np.maximum(np.asarray(z, dtype=np.float64), 0.0)
    peak = float(np.max(a)) or 1.0
    u = a / peak
    return np.arcsinh(u / p) / np.arcsinh(1.0 / p)


def _bloom(z: NDArray, sigma: float = 1.15, mix: float = 0.28) -> NDArray[np.float64]:
    a = np.asarray(z, dtype=np.float64)
    try:
        from scipy.ndimage import gaussian_filter

        return a + mix * gaussian_filter(a, sigma=sigma)
    except Exception:
        return a


def _hsv_to_rgb(h: NDArray, s: NDArray, v: NDArray) -> NDArray[np.float64]:
    h = np.mod(np.asarray(h, dtype=np.float64), 1.0)
    s = np.clip(np.asarray(s, dtype=np.float64), 0.0, 1.0)
    v = np.clip(np.asarray(v, dtype=np.float64), 0.0, 1.0)
    c = v * s
    hp = h * 6.0
    x = c * (1.0 - np.abs(np.mod(hp, 2.0) - 1.0))
    m = v - c
    rgb = np.zeros(h.shape + (3,), dtype=np.float64)
    i = np.floor(hp).astype(np.int64) % 6
    cond = [
        (i == 0, (c, x, 0.0)),
        (i == 1, (x, c, 0.0)),
        (i == 2, (0.0, c, x)),
        (i == 3, (0.0, x, c)),
        (i == 4, (x, 0.0, c)),
        (i == 5, (c, 0.0, x)),
    ]
    for mask, (r, g, b) in cond:
        rgb[mask, 0] = r if np.isscalar(r) else r[mask]
        rgb[mask, 1] = g if np.isscalar(g) else g[mask]
        rgb[mask, 2] = b if np.isscalar(b) else b[mask]
    rgb += m[..., None]
    return np.clip(rgb, 0.0, 1.0)


def _to_u8(rgb: NDArray) -> RGB:
    return np.clip(np.asarray(rgb) * 255.0, 0, 255).astype(np.uint8)


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
    return apply_lut(_stretch(_bloom(np.abs(np.asarray(field)) ** 2)), _INTENSITY_LUT)


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
    """FR 1–3: collimated femtosecond pulse — white core, chromatic halo."""
    x, y = cartesian_grid(n, 2.35)
    rho, phi = polar_from_cartesian(x, y)
    w = float(w0) * (0.42 + 0.03 * np.sin(2.0 * np.pi * frame))
    core = np.exp(-(rho**2) / (w * 0.48) ** 2)
    rch = np.exp(-(rho**2) / (w * 1.28) ** 2)
    gch = np.exp(-(rho**2) / (w * 1.00) ** 2)
    bch = np.exp(-(rho**2) / (w * 0.78) ** 2)
    rgb = np.stack([rch, gch, bch], axis=-1)
    rgb = rgb + core[..., None] * 1.45
    # spectral halo: blue near core → red at the edge (not a single green ring)
    t = np.clip((rho / (2.1 * w)), 0.0, 1.0)
    halo = np.exp(-((rho - 1.05 * w) ** 2) / (0.38 * w) ** 2)
    rgb = rgb + 0.95 * _hsv_to_rgb(0.62 - 0.62 * t, 0.88 * np.ones_like(t), halo)
    rings = (np.sin(16.0 * rho / max(w, 1e-6)) ** 2) * np.exp(-(rho**2) / (2.6 * w) ** 2)
    rgb = rgb + 0.10 * rings[..., None]
    lum = np.max(rgb, axis=-1)
    bloomed = _bloom(lum, sigma=max(0.8, n / 180.0), mix=0.22)
    rgb = rgb * (bloomed / (lum + 1e-9))[..., None]
    rgb = rgb / (float(np.max(rgb)) or 1.0)
    rgb = rgb**0.82
    return _to_u8(rgb)


def pulse_streak(n: int = 96, frame: float = 0.0, nx: int | None = None, ny: int | None = None) -> RGB:
    """FR 4–5: elongated / temporally shaped pulse (x vs z, chirped)."""
    nx = int(n if nx is None else nx)
    ny = int(n if ny is None else ny)
    z = np.linspace(0.0, 1.0, nx)
    x = np.linspace(-2.2, 2.2, ny)
    Z, X = np.meshgrid(z, x, indexing="xy")
    z0 = 0.46 + 0.08 * np.sin(2.0 * np.pi * frame)
    tau = 0.16
    env = np.exp(-(X**2) / 0.18) * np.exp(-((Z - z0) ** 2) / (2.0 * tau**2))
    env = env + 0.22 * np.exp(-(X**2) / 0.55) * np.exp(-((Z - z0) ** 2) / (2.0 * (tau * 1.85) ** 2))
    env = env + 0.08 * np.exp(-(X**2) / 0.10) * np.exp(-((Z - (z0 - 0.22)) ** 2) / (2.0 * (tau * 0.55) ** 2))
    env = _bloom(env, sigma=max(0.7, nx / 220.0), mix=0.3)
    env = _stretch(env, p=0.05)
    wl = 430.0 + 300.0 * np.clip(Z, 0.0, 1.0)
    rgb = spectral_rgb(wl) * env[..., None]
    rgb = rgb / (float(np.max(rgb)) or 1.0)
    return _to_u8(rgb)


def helical_length_view(
    ells: tuple[int, ...] = (1,),
    n: int = 96,
    pitch: float = 2.35,
    frame: float = 0.0,
    layers: int | None = None,
    nx: int | None = None,
    ny: int | None = None,
    z_len: float = 11.0,
    spectral: bool = True,
    x_span: float = 3.5,
) -> RGB:
    """Side-on nested helical tubes (length / propagation perspective)."""
    nx = int(n if nx is None else nx)
    ny = int(n if ny is None else ny)
    z = np.linspace(0.0, z_len, nx)
    x = np.linspace(-float(x_span), float(x_span), ny)
    Z, X = np.meshgrid(z, x, indexing="xy")
    ells = tuple(ells if layers is None else range(1, int(layers) + 1))
    phase0 = 2.0 * np.pi * (frame % 1.0)
    dens = np.zeros((ny, nx), dtype=np.float64)
    hue = np.zeros((ny, nx), dtype=np.float64)
    weight = np.zeros((ny, nx), dtype=np.float64)
    n_e = max(1, len(ells))
    for k, ell in enumerate(ells):
        a = 1.0 / (1.0 + 0.16 * k)
        r0 = 0.55 + 0.70 * k
        w = 0.20 + 0.03 * k
        persp = 1.0 - 0.14 * (Z / z_len)
        cx = r0 * persp * np.cos(int(ell) * Z * (2.0 * np.pi / pitch) + phase0)
        dist = np.abs(X - cx)
        wall = np.exp(-((dist - 0.35 * w) ** 2) / (2.0 * (0.48 * w) ** 2))
        core = np.exp(-(dist**2) / (2.0 * (0.42 * w) ** 2))
        depth = np.exp(-((X - 0.72 * cx) ** 2) / (2.0 * (1.15 * w) ** 2))
        layer = a * (0.40 * wall + 1.05 * core + 0.18 * depth)
        dens = dens + layer
        hk = (0.08 + 0.72 * k / max(1, n_e - 0.4) + 0.12 * (Z / z_len)) % 1.0
        hue = hue + hk * layer
        weight = weight + layer
    dens = _bloom(dens, sigma=max(0.6, nx / 260.0), mix=0.22)
    v = _stretch(dens, p=0.04)
    if spectral:
        h = np.divide(hue, np.maximum(weight, 1e-9))
        rgb = _hsv_to_rgb(h, 0.72 * np.ones_like(v), v)
        return _to_u8(rgb)
    return apply_lut(v, _INTENSITY_LUT)


def nested_rings(x: NDArray, y: NDArray, ells: tuple[int, ...] = (1, 2, 3), w0: float = 1.0) -> RGB:
    """Concentric helical rings (intensity) with a light azimuthal phase tint."""
    rho, phi = polar_from_cartesian(x, y)
    span = float(np.max(np.abs(x))) or 1.0
    w_eff = 0.26 * span
    I = np.zeros_like(np.asarray(x, dtype=np.float64))
    field = np.zeros_like(x, dtype=np.complex128)
    n_e = max(1, len(ells))
    for i, ell in enumerate(ells):
        mode = lg_mode_xy(int(ell), x, y, w0=w_eff * (1.0 + 0.06 * i))
        field = field + (0.84**i) * mode
        ring = np.abs(mode) ** 2
        peak = float(np.max(ring)) or 1.0
        r0 = (0.20 + 0.68 * (i + 1) / n_e) * span * 0.92
        shell = np.exp(-((rho - r0) ** 2) / (2.0 * (0.038 * span) ** 2))
        I = I + (0.92**i) * (0.50 * ring / peak + 0.85 * shell)
    I = _stretch(_bloom(I, sigma=max(0.55, x.shape[0] / 220.0), mix=0.2), p=0.045)
    base = apply_lut(I, _INTENSITY_LUT).astype(np.float64) / 255.0
    hue = np.mod((np.angle(field) + np.pi) / (2.0 * np.pi), 1.0)
    tint = _hsv_to_rgb(hue, 0.40 * I, I)
    rgb = 0.78 * base + 0.22 * tint
    return _to_u8(rgb)


def quaternion_phase_mask(x: NDArray, y: NDArray, ell: int = 1) -> RGB:
    """Spiral phase with a 2φ quaternion warp, vortex-intensity gated."""
    rho, phi = polar_from_cartesian(x, y)
    phase = int(ell) * phi + 0.38 * np.sin(2.0 * phi) + 0.08 * np.sin(4.0 * phi)
    I = np.abs(lg_mode_xy(int(ell), x, y, w0=0.55 * (float(np.max(np.abs(x))) or 1.0))) ** 2
    I = _stretch(_bloom(I, sigma=max(0.7, x.shape[0] / 180.0)), p=0.05)
    rgb = phase_rgb(phase).astype(np.float64) / 255.0
    gate = 0.08 + 0.92 * I
    rgb = rgb * gate[..., None]
    return _to_u8(rgb)


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
        if x is not None and y is not None:
            return quaternion_phase_mask(x, y, ell=ell)
        xx, yy = cartesian_grid(n, 2.2)
        return quaternion_phase_mask(xx, yy, ell=ell)
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
        return helical_length_view(ells=(max(1, int(abs(ell))),), n=n, frame=frame, nx=max(n, int(n * 1.35)), ny=n)
    if stage == "helical":
        ells = tuple(range(1, max(2, int(layers)) + 1))
        return helical_length_view(ells=ells, n=n, frame=frame, pitch=2.15, nx=max(n, int(n * 1.35)), ny=n)
    if stage == "detect":
        ells = tuple(range(1, max(4, int(layers) + 1) + 1))
        return helical_length_view(
            ells=ells, n=n, frame=frame, pitch=1.75, z_len=13.5, nx=max(n, int(n * 1.45)), ny=n
        )
    return pulse_streak(n=n, frame=frame)


def panel_meta(monitor_title: str, scale: str, frame_ids: list[int]) -> dict[str, Any]:
    if frame_ids:
        lo, hi = min(frame_ids), max(frame_ids)
        label = f"FR {lo}" if lo == hi else f"FR {lo}–{hi}"
    else:
        label = ""
    return {"title": monitor_title, "scale": scale, "frame_label": label}


def monitor_asset_dirs() -> list:
    from pathlib import Path

    from vqc_workbench.core.config import workbench_root

    pkg = Path(__file__).resolve().parent.parent / "assets" / "beam_monitors"
    docs = workbench_root() / "docs" / "figures" / "beam_monitors"
    return [pkg, docs]


def load_monitor_asset(stage: str, view: str) -> RGB | None:
    name = MONITOR_ASSETS.get((stage, view))
    if not name:
        return None
    for folder in monitor_asset_dirs():
        path = folder / name
        if not path.is_file():
            continue
        try:
            from matplotlib.image import imread

            arr = imread(str(path))
        except Exception:
            try:
                from PIL import Image

                arr = np.asarray(Image.open(path).convert("RGB"))
            except Exception:
                continue
        rgb = np.asarray(arr)
        if rgb.ndim == 2:
            rgb = np.stack([rgb, rgb, rgb], axis=-1)
        if rgb.shape[-1] == 4:
            rgb = rgb[..., :3]
        if rgb.dtype != np.uint8:
            rgb = np.clip(rgb * (255.0 if float(np.max(rgb)) <= 1.5 else 1.0), 0, 255).astype(np.uint8)
        return rgb
    return None


def save_monitor_asset(rgb: RGB, stage: str, view: str, directory=None):
    from pathlib import Path

    name = MONITOR_ASSETS[(stage, view)]
    folder = Path(directory) if directory is not None else monitor_asset_dirs()[0]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    from matplotlib.image import imsave

    imsave(path, rgb)
    return path


def render_monitor_set(out_dir=None, n_ax: int = 384, n_st: tuple[int, int] = (220, 420)) -> dict[str, Any]:
    """Write the eight FR 1–16 monitor PNGs from Workbench / LG propagation."""
    from pathlib import Path

    from vqc_workbench.ladder.prototype import prototype_monitor_images

    dirs = [Path(out_dir)] if out_dir is not None else monitor_asset_dirs()
    images = prototype_monitor_images(n_ax=n_ax, n_st=n_st)
    written: dict[str, str] = {}
    for (stage, view), rgb in images.items():
        for folder in dirs:
            path = save_monitor_asset(rgb, stage, view, directory=folder)
            written[f"{stage}:{view}"] = str(path)
    return written


def monitor_image(
    stage: str,
    view: str,
    *,
    field: NDArray | None = None,
    phase_mask: NDArray | None = None,
    x: NDArray | None = None,
    y: NDArray | None = None,
    ell: int = 1,
    layers: int = 3,
    frame: float = 0.0,
    n: int = 96,
    override: RGB | None = None,
) -> RGB:
    """HITL override → cached PNG → procedural fallback."""
    if override is not None:
        return override
    cached = load_monitor_asset(stage, view)
    if cached is not None:
        return cached
    if view == "axial":
        return axial_for_stage(
            stage,
            field=field,
            phase_mask=phase_mask,
            x=x,
            y=y,
            ell=ell,
            layers=layers,
            frame=frame,
            n=n,
        )
    return st_for_stage(stage, ell=ell, layers=layers, frame=frame, n=n)
