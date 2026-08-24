"""Trajectoid-style shells with phase-mask trenches.

Analytic Jacobi–Anger trenches always work and keep ℓ = winding − n_trenches.
``live=True`` replaces the cosine trench with ``flux_trajectoid.generate_shell``
(rolling path + 1-D trench / 2-D modulator). Missing the package raises
``TrajectoidLiveUnavailable``. Workbench imports flux_trajectoid; never the reverse.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian


class TrajectoidLiveUnavailable(RuntimeError):
    pass


def _hash_seed(payload_hash: str | None) -> int:
    raw = (payload_hash or "vqc").encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def _load_flux_trajectoid():
    try:
        from vqc_workbench.adapters import import_flux_trajectoid

        return import_flux_trajectoid()
    except ImportError as exc:
        raise TrajectoidLiveUnavailable(
            "flux_trajectoid is not importable. pip install -e ../flux_trajectoid "
            "or keep the checkout at ~/Projects/flux_trajectoid."
        ) from exc


def _azimuthal_from_1d(signal: NDArray | None, phi: NDArray) -> NDArray[np.float64]:
    if signal is None:
        return np.zeros_like(phi, dtype=np.float64)
    arr = np.asarray(signal, dtype=np.float64).ravel()
    if arr.size == 0:
        return np.zeros_like(phi, dtype=np.float64)
    idx = ((phi + np.pi) / (2.0 * np.pi) * (arr.size - 1)).astype(int)
    return arr[np.clip(idx, 0, arr.size - 1)]


def _sample_on_grid(src: NDArray, extent: float, x: NDArray, y: NDArray) -> NDArray[np.float64]:
    from scipy.ndimage import map_coordinates

    src = np.asarray(src, dtype=np.float64)
    h, w = src.shape
    gx = (np.asarray(x, dtype=np.float64) + extent) / (2.0 * extent) * (w - 1)
    gy = (np.asarray(y, dtype=np.float64) + extent) / (2.0 * extent) * (h - 1)
    return map_coordinates(src, [gy, gx], order=1, mode="nearest")


def _live_trench(shell: Any, x: NDArray, y: NDArray) -> NDArray[np.float64]:
    """Map a live ShellGeometry onto the workbench (x, y) grid."""
    rho, phi = polar_from_cartesian(x, y)
    trench = _azimuthal_from_1d(getattr(shell, "phase_trench_mask", None), phi)
    curv = _azimuthal_from_1d(getattr(shell, "curvature_signal", None), phi)
    live = trench + 0.25 * np.tanh(curv) * np.log1p(rho)
    try:
        import importlib

        modulator = importlib.import_module("flux_trajectoid.shell.modulator")
        extent = float(max(np.max(np.abs(x)), np.max(np.abs(y)), 1e-6))
        n = int(max(x.shape))
        mod = modulator.shell_to_phase_mask(shell, grid_size=min(n, 96), extent=extent)
        live = 0.45 * live + 0.55 * _sample_on_grid(mod.phase_mask, extent, x, y)
    except Exception:
        pass
    peak = float(np.max(np.abs(live))) or 1.0
    return (live - float(np.mean(live))) / peak


@register("trajectoid")
class TrajectoidShell(ParametricCell):
    """Rolling-path trench mask: analytic Jacobi–Anger or live generate_shell."""

    kind = "trajectoid"

    def __init__(self, name: str = "trajectoid", params=None, material=None):
        params = dict(params or {})
        params.setdefault("payload_hash", None)
        params.setdefault("n_trenches", 8)
        params.setdefault("winding", 2)
        params.setdefault("trench_depth_rad", np.pi)
        params.setdefault("live", False)
        params.setdefault("build_3d", False)
        params.setdefault("n_points", 128)
        params.setdefault("scale_grid", 3)
        params.setdefault("scale_max_iter", 4)
        super().__init__(name=name, params=params, material=material)
        self._shell: Any = None
        self._shell_key: tuple | None = None

    def uses_live_shell(self) -> bool:
        return bool(self.params.get("live"))

    def live_shell(self):
        """Return the cached ``ShellGeometry``, generating it if needed."""
        if not self.uses_live_shell():
            return None
        payload = str(self.params.get("payload_hash") or "vqc")
        seed = _hash_seed(payload)
        key = (
            payload,
            seed,
            int(self.params.get("n_trenches", 8)),
            int(self.params.get("n_points", 128)),
            int(self.params.get("scale_grid", 3)),
            int(self.params.get("scale_max_iter", 4)),
            bool(self.params.get("build_3d", False)),
        )
        if self._shell is not None and self._shell_key == key:
            return self._shell
        _load_flux_trajectoid()
        import importlib

        generate_shell = importlib.import_module("flux_trajectoid.shell.generator").generate_shell
        n_trenches = int(self.params.get("n_trenches", 8))
        self._shell = generate_shell(
            payload,
            seed=seed,
            n_points=int(self.params.get("n_points", 128)),
            n_harmonics=max(4, min(24, n_trenches)),
            build_3d=bool(self.params.get("build_3d", False)),
            scale_grid=int(self.params.get("scale_grid", 3)),
            scale_max_iter=int(self.params.get("scale_max_iter", 4)),
            n_lat=24,
            n_lon=48,
        )
        self._shell_key = key
        return self._shell

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, y = grid
        rho, phi = polar_from_cartesian(x, y)
        winding = int(self.params["winding"])
        depth = float(self.params["trench_depth_rad"])
        if self.uses_live_shell():
            trench = _live_trench(self.live_shell(), x, y)
        else:
            n = int(self.params["n_trenches"])
            rng = np.random.default_rng(_hash_seed(self.params.get("payload_hash")))
            k = 2.0 + 0.15 * rng.standard_normal()
            trench = np.cos(n * phi + winding * np.log1p(rho) * k)
        phase = depth * 0.5 * (1.0 + trench)
        helical = winding * phi
        return np.exp(1j * (phase + helical))

    def to_geometry_dict(self):
        spec = super().to_geometry_dict()
        spec["engine"] = "analytic"
        spec["live_shell"] = False
        if not self.uses_live_shell():
            return spec
        shell = self.live_shell()
        spec["engine"] = "flux_trajectoid.generate_shell"
        spec["live_shell"] = True
        spec["generator"] = "flux_trajectoid.generate_shell"
        meta = dict(getattr(shell, "metadata", None) or {})
        fp = getattr(shell, "fourier_fingerprint", None)
        spec["shell"] = {
            "kx": float(getattr(shell, "kx", 0.0)),
            "ky": float(getattr(shell, "ky", 0.0)),
            "mismatch_deg": float(getattr(shell, "mismatch_deg", 0.0)),
            "tilt_deg": float(getattr(shell, "tilt_deg", 0.0)),
            "rolling_radius": float(getattr(shell, "rolling_radius", 1.0)),
            "is_3d": bool(getattr(shell, "is_3d", False)),
            "payload_hash": meta.get("payload_hash"),
            "fourier_fingerprint": None if fp is None else np.asarray(fp).astype(float).tolist(),
        }
        return spec
