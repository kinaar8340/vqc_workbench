"""Full-wave backends with a shared modal-coefficient / S-matrix interface.

The fast path remains the thin-element modal engine. Full-wave backends emit
the same ``ell`` / ``coefficients`` / ``intensity`` vectors so they can be
cached and handed to the VQC pipeline.

Always available
    ``scalar`` — angular-spectrum scalar diffraction (full-wave *lite*).
    ``modal``  — adapter around :class:`ModalSimulator` for side-by-side compares.

Opt-in (fail loudly if missing)
    ``meep`` — MIT Meep FDTD.
    ``rcwa`` — ``grcwa`` or ``nannos``.
"""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import Structure
from vqc_workbench.simulation.lg import gaussian_beam, project_oam_spectrum
from vqc_workbench.simulation.modal import ModeResult, ModalSimulator
from vqc_workbench.utils.grid import cartesian_grid


class FullWaveUnavailable(RuntimeError):
    pass


def _jsonable(value: Any) -> Any:
    if callable(value):
        return {"__callable__": getattr(value, "__name__", "callable")}
    if isinstance(value, np.ndarray):
        return {"__ndarray__": True, "shape": list(value.shape), "hash": hashlib.sha256(value.tobytes()).hexdigest()[:16]}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass
class FullWaveResult:
    """Solver-agnostic modal snapshot consumed by the VQC pipeline."""

    backend: str
    ell: NDArray[np.int64]
    coefficients: NDArray[np.complex128]
    intensity: NDArray[np.float64]
    S: NDArray[np.complex128] | None = None
    T: NDArray[np.complex128] | None = None
    cached: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def dominant_ell(self) -> int:
        return int(self.ell[int(np.argmax(np.abs(self.coefficients)))])

    def expectation_ell(self) -> float:
        return float(np.sum(self.ell.astype(float) * self.intensity))

    def weight_dict(self) -> dict[int, complex]:
        return {int(e): complex(c) for e, c in zip(self.ell, self.coefficients)}

    def smatrix_proxy(self) -> NDArray[np.complex128]:
        t = self.T if self.T is not None else np.diag(self.coefficients)
        n = t.shape[0]
        r = np.zeros((n, n), dtype=np.complex128)
        return np.block([[r, t], [t, r]])

    def to_cache_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "ell": self.ell,
            "coefficients": self.coefficients,
            "intensity": self.intensity,
            "S": self.S,
            "T": self.T,
            "extras": {k: v for k, v in self.extras.items() if _is_plain(v)},
        }


def _is_plain(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None), list, dict))


def result_from_modes(modes: ModeResult, backend: str = "modal") -> FullWaveResult:
    t = np.diag(modes.coefficients)
    n = t.shape[0]
    r = np.zeros((n, n), dtype=np.complex128)
    s = np.block([[r, t], [t, r]])
    return FullWaveResult(
        backend=backend,
        ell=modes.ell,
        coefficients=modes.coefficients,
        intensity=modes.intensity,
        S=s,
        T=t,
        extras={"wavelength_nm": modes.wavelength_nm, "L_max": modes.L_max},
    )


def _normalize_intensity(coefficients: NDArray) -> NDArray[np.float64]:
    mag2 = np.abs(coefficients) ** 2
    total = float(np.sum(mag2)) or 1.0
    return mag2 / total


def pack_oam_result(
    field: NDArray[np.complex128],
    x: NDArray,
    y: NDArray,
    *,
    L_max: int,
    w0: float,
    backend: str,
    extras: dict[str, Any] | None = None,
) -> FullWaveResult:
    """Project a 2-D field onto the LG ladder and wrap a FullWaveResult."""
    weights = project_oam_spectrum(field, x, y, L_max=int(L_max), w0=float(w0))
    ells = np.arange(-int(L_max), int(L_max) + 1, dtype=np.int64)
    coeffs = np.array([weights[int(e)] for e in ells], dtype=np.complex128)
    t = np.diag(coeffs)
    n = t.shape[0]
    z = np.zeros((n, n), dtype=np.complex128)
    return FullWaveResult(
        backend=backend,
        ell=ells,
        coefficients=coeffs,
        intensity=_normalize_intensity(coeffs),
        S=np.block([[z, t], [t, z]]),
        T=t,
        extras=dict(extras or {}),
    )


class FullWaveCache:
    """In-memory cache keyed by a stable structure/backend hash. Optional disk."""

    def __init__(self, disk_dir: str | Path | None = None):
        self._mem: dict[str, FullWaveResult] = {}
        self.disk_dir = Path(disk_dir) if disk_dir is not None else None

    def key(
        self,
        structure: Structure,
        *,
        backend: str,
        L_max: int,
        wavelength_nm: float,
        grid_size: int,
        extra: dict[str, Any] | None = None,
    ) -> str:
        payload = {
            "kind": structure.kind,
            "name": structure.name,
            "params": _jsonable(structure.params),
            "material": None if structure.material is None else structure.material.name,
            "backend": backend,
            "L_max": int(L_max),
            "wavelength_nm": float(wavelength_nm),
            "grid_size": int(grid_size),
            "extra": _jsonable(extra or {}),
        }
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, key: str) -> FullWaveResult | None:
        hit = self._mem.get(key)
        if hit is not None:
            clone = deepcopy(hit)
            clone.cached = True
            return clone
        if self.disk_dir is None:
            return None
        path = self.disk_dir / f"{key}.npz"
        if not path.is_file():
            return None
        data = np.load(path, allow_pickle=True)
        result = FullWaveResult(
            backend=str(data["backend"]),
            ell=np.asarray(data["ell"], dtype=np.int64),
            coefficients=np.asarray(data["coefficients"], dtype=np.complex128),
            intensity=np.asarray(data["intensity"], dtype=np.float64),
            S=None if data["S"].shape == () else np.asarray(data["S"]),
            T=None if data["T"].shape == () else np.asarray(data["T"]),
            cached=True,
            extras=json.loads(str(data["extras"])),
        )
        self._mem[key] = result
        return deepcopy(result)

    def put(self, key: str, result: FullWaveResult) -> None:
        stored = deepcopy(result)
        stored.cached = False
        self._mem[key] = stored
        if self.disk_dir is None:
            return
        self.disk_dir.mkdir(parents=True, exist_ok=True)
        np.savez(
            self.disk_dir / f"{key}.npz",
            backend=result.backend,
            ell=result.ell,
            coefficients=result.coefficients,
            intensity=result.intensity,
            S=result.S if result.S is not None else np.array(None),
            T=result.T if result.T is not None else np.array(None),
            extras=json.dumps({k: v for k, v in result.extras.items() if _is_plain(v)}),
        )


class FullWaveBackend(ABC):
    name: str = "fullwave"

    @abstractmethod
    def run(
        self,
        structure: Structure,
        *,
        L_max: int = 8,
        wavelength_nm: float = 1550.0,
        grid_size: int = 128,
        w0: float = 1.0,
        extent: float = 4.0,
        sources: Any = None,
        monitors: Any = None,
        **kwargs: Any,
    ) -> FullWaveResult:
        ...


def angular_spectrum_propagate(
    field: NDArray[np.complex128],
    dx: float,
    wavelength: float,
    z: float,
) -> NDArray[np.complex128]:
    """Band-limited angular-spectrum propagator (scalar Helmholtz)."""
    ny, nx = field.shape
    fx = np.fft.fftfreq(nx, d=dx)
    fy = np.fft.fftfreq(ny, d=dx)
    fx_g, fy_g = np.meshgrid(fx, fy, indexing="xy")
    k = 2.0 * np.pi / float(wavelength)
    kz2 = k**2 - (2.0 * np.pi * fx_g) ** 2 - (2.0 * np.pi * fy_g) ** 2
    evanescent = kz2 < 0
    kz = np.sqrt(np.maximum(kz2, 0.0))
    transfer = np.exp(1j * kz * float(z))
    transfer = np.where(evanescent, 0.0, transfer)
    return np.fft.ifft2(np.fft.fft2(field) * transfer)


class ModalBackend(FullWaveBackend):
    """Wrap the thin-element modal engine as a FullWaveResult producer."""

    name = "modal"

    def __init__(self, modal: ModalSimulator | None = None):
        self.modal = modal or ModalSimulator()

    def run(self, structure: Structure, **kwargs: Any) -> FullWaveResult:
        modes = self.modal.structure_to_modes(
            structure,
            L_max=kwargs.get("L_max"),
            wavelength_nm=kwargs.get("wavelength_nm"),
            grid_size=kwargs.get("grid_size"),
            w0=kwargs.get("w0"),
        )
        return result_from_modes(modes, backend="modal")


class ScalarDiffractionBackend(FullWaveBackend):
    """Angular-spectrum scalar diffraction through the thin-element mask.

    Always available (numpy/scipy only). At ``z=0`` this matches the modal
    thin-element field; a small ``z`` adds Fresnel diffraction so it is a
    stricter check than the modal path without requiring Meep.
    """

    name = "scalar"

    def run(
        self,
        structure: Structure,
        *,
        L_max: int = 8,
        wavelength_nm: float = 1550.0,
        grid_size: int = 128,
        w0: float = 1.0,
        extent: float = 4.0,
        sources: Any = None,
        monitors: Any = None,
        z: float = 0.15,
        **kwargs: Any,
    ) -> FullWaveResult:
        x, y = cartesian_grid(int(grid_size), float(extent))
        mask = structure.to_phase_mask((x, y), float(wavelength_nm))
        field = gaussian_beam(x, y, w0=float(w0)) * mask
        dx = float(x[0, 1] - x[0, 0]) if x.shape[1] > 1 else 1.0
        # Grid units are w0; treat wavelength in the same units (~0.1 w0 typical).
        lam = max(float(wavelength_nm) * 1e-6, 0.05)
        if abs(float(z)) > 0:
            field = angular_spectrum_propagate(field, dx=dx, wavelength=lam, z=float(z))
        return pack_oam_result(
            field,
            x,
            y,
            L_max=int(L_max),
            w0=float(w0),
            backend="scalar",
            extras={
                "z": float(z),
                "wavelength_nm": float(wavelength_nm),
                "L_max": int(L_max),
                "grid_size": int(grid_size),
            },
        )


class MeepBackend(FullWaveBackend):
    """FDTD backend. Requires MIT Meep; raises if it is not importable."""

    name = "meep"

    def run(self, structure: Structure, **kwargs: Any) -> FullWaveResult:
        try:
            import meep as mp  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise FullWaveUnavailable(
                "Meep is not installed. Use the `scalar` backend for angular-spectrum "
                "diffraction, or install MIT Meep and retry with backend='meep'."
            ) from exc
        return self._run_meep(structure, **kwargs)

    def _run_meep(
        self,
        structure: Structure,
        *,
        L_max: int = 8,
        wavelength_nm: float = 1550.0,
        grid_size: int = 48,
        w0: float = 1.0,
        extent: float = 4.0,
        resolution: int = 16,
        **kwargs: Any,
    ) -> FullWaveResult:
        import meep as mp  # type: ignore

        # Opt-in FDTD. Default off so `pytest` stays fast even if Meep is present.
        if os.environ.get("VQC_MEEP_RUN", "").lower() not in {"1", "true", "yes"}:
            raise FullWaveUnavailable(
                "Meep is installed. Set VQC_MEEP_RUN=1 to run FDTD "
                "(spiral / binary grating reference cells)."
            )

        x, y = cartesian_grid(int(grid_size), float(extent))
        mask = structure.to_phase_mask((x, y), float(wavelength_nm))
        ny, nx = mask.shape
        sx = sy = 2.0 * float(extent)
        # Thin phase plate → 2-D ε(x,y). n = 1 + φ/2π maps [−π,π] onto ~[0.5, 1.5].
        n_map = 1.0 + np.angle(mask) / (2.0 * np.pi)
        eps = np.clip(n_map, 1.0, 2.5) ** 2
        eps_max = float(np.max(eps))
        weights = np.clip((eps - 1.0) / max(eps_max - 1.0, 1e-9), 0.0, 1.0)
        # Meep MaterialGrid wants (Nx, Ny) with x the first axis.
        weights_mg = np.ascontiguousarray(weights.T)

        try:
            geom = [
                mp.Block(
                    center=mp.Vector3(0, 0, 0),
                    size=mp.Vector3(sx, sy, mp.inf),
                    material=mp.MaterialGrid(
                        grid_size=mp.Vector3(nx, ny),
                        medium1=mp.Medium(epsilon=1.0),
                        medium2=mp.Medium(epsilon=eps_max),
                        weights=weights_mg,
                    ),
                )
            ]
            src = [
                mp.Source(
                    mp.GaussianSource(wavelength=1.0, width=2.0),
                    component=mp.Ez,
                    center=mp.Vector3(0, 0, 0),
                    size=mp.Vector3(sx * 0.9, sy * 0.9, 0),
                    amp_func=lambda p: float(
                        np.exp(-(p.x**2 + p.y**2) / max(float(w0) ** 2, 1e-6))
                    ),
                )
            ]
            sim = mp.Simulation(
                cell_size=mp.Vector3(sx, sy, 0),
                geometry=geom,
                sources=src,
                resolution=int(resolution),
                boundary_layers=[mp.PML(0.4)],
            )
            sim.run(until=12)
            ez = np.array(sim.get_array(center=mp.Vector3(), size=mp.Vector3(sx, sy, 0), component=mp.Ez))
        except Exception as exc:
            raise FullWaveUnavailable(f"Meep FDTD run failed: {exc}") from exc

        # Resample Ez onto the workbench grid and project OAM — same FullWaveResult
        # contract as modal/scalar. No multiplying back the analytic mask.
        if ez.ndim == 1:
            raise FullWaveUnavailable("Meep returned a 1-D Ez array; expected a 2-D plane.")
        field = _resample_complex(ez.astype(np.complex128), x.shape)
        return pack_oam_result(
            field,
            x,
            y,
            L_max=int(L_max),
            w0=float(w0),
            backend="meep",
            extras={
                "resolution": int(resolution),
                "meep_version": getattr(mp, "__version__", None),
                "kind": structure.kind,
            },
        )


def _resample_complex(src: NDArray[np.complex128], shape: tuple[int, int]) -> NDArray[np.complex128]:
    """Nearest-neighbor resample of a 2-D field onto ``shape``."""
    ny, nx = int(shape[0]), int(shape[1])
    sy, sx = src.shape[:2]
    yi = np.linspace(0, sy - 1, ny).astype(int)
    xi = np.linspace(0, sx - 1, nx).astype(int)
    return src[yi][:, xi]


class RCWABackend(FullWaveBackend):
    """Periodic grating / metasurface backend. Tries ``grcwa`` then ``nannos``."""

    name = "rcwa"

    def run(self, structure: Structure, **kwargs: Any) -> FullWaveResult:
        engine = None
        engine_name = None
        for mod in ("grcwa", "nannos"):
            try:
                engine = __import__(mod)
                engine_name = mod
                break
            except ImportError:
                continue
        if engine is None:
            raise FullWaveUnavailable(
                "No RCWA engine found (tried grcwa, nannos). Use backend='scalar' "
                "or install an RCWA package."
            )
        # Hand the structure geometry to the engine; a full layer stack is a
        # follow-up. For now we project the thin-element mask so the return
        # type stays consistent, and record the live engine name.
        scalar = ScalarDiffractionBackend()
        result = scalar.run(structure, **kwargs)
        result.backend = "rcwa"
        result.extras["engine"] = engine_name
        result.extras["note"] = "RCWA engine present; modal coefficients via scalar projector pending layer mapping"
        return result


def get_backend(name: str, modal: ModalSimulator | None = None) -> FullWaveBackend:
    key = name.lower().strip()
    if key in {"modal"}:
        return ModalBackend(modal=modal)
    if key in {"scalar", "asp", "diffraction"}:
        return ScalarDiffractionBackend()
    if key in {"meep", "fdtd"}:
        return MeepBackend()
    if key in {"rcwa", "grcwa", "nannos"}:
        return RCWABackend()
    raise KeyError(f"unknown full-wave backend {name!r}; try modal, scalar, meep, rcwa")


class FullWaveEngine:
    """Cached dispatcher: structure + backend → FullWaveResult."""

    def __init__(self, cache: FullWaveCache | None = None, modal: ModalSimulator | None = None):
        self.cache = cache or FullWaveCache()
        self.modal = modal

    def run(
        self,
        structure: Structure,
        backend: str = "scalar",
        *,
        L_max: int = 8,
        wavelength_nm: float = 1550.0,
        grid_size: int = 128,
        w0: float = 1.0,
        extent: float = 4.0,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> FullWaveResult:
        extra = {k: v for k, v in kwargs.items() if _is_plain(v) or isinstance(v, (int, float, str, bool))}
        key = self.cache.key(
            structure,
            backend=backend,
            L_max=L_max,
            wavelength_nm=wavelength_nm,
            grid_size=grid_size,
            extra=extra,
        )
        if use_cache:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        be = get_backend(backend, modal=self.modal)
        result = be.run(
            structure,
            L_max=L_max,
            wavelength_nm=wavelength_nm,
            grid_size=grid_size,
            w0=w0,
            extent=extent,
            **kwargs,
        )
        if use_cache:
            self.cache.put(key, result)
        return result
