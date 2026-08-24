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


def phase_to_slab_index(
    mask: NDArray,
    *,
    thickness: float = 1.0,
    wavelength: float = 1.0,
    n_lo: float = 1.2,
    n_hi: float | None = None,
    encoding: str = "full_2pi",
    n0: float = 1.0,
    dn_amp: float = 0.4,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Map a complex thin-element mask onto a dielectric index n(x,y).

    ``full_2pi`` (default) puts the wrapped phase onto ``[n_lo, n_hi]`` with
    ``(n_hi − n_lo) · d = λ`` so a 2π helix is not clipped to vacuum.
    ``legacy`` is the old ``n = clip(1 + φ λ / 2π d)`` path (charge-wrong).
    """
    d = max(float(thickness), 1e-9)
    lam = float(wavelength)
    enc = str(encoding or "full_2pi")
    if enc == "legacy":
        if float(n0) > 1.0:
            n_map = float(n0) + float(dn_amp) * (np.angle(mask) / np.pi)
            n_map = np.clip(n_map, 1.01, 2.8)
            meta = {
                "encoding": "legacy_centered",
                "slab_n0": float(n0),
                "slab_dn": float(dn_amp),
                "slab_thickness": d,
                "wavelength": lam,
            }
        else:
            delta_n = np.angle(mask) * lam / (2.0 * np.pi * d)
            n_map = np.clip(1.0 + delta_n, 1.0, 2.8)
            meta = {
                "encoding": "legacy_clip",
                "slab_n0": 1.0,
                "slab_dn": None,
                "slab_thickness": d,
                "wavelength": lam,
            }
        return np.asarray(n_map, dtype=np.float64), meta

    n_lo = float(n_lo)
    if n_hi is None:
        n_hi = n_lo + lam / d
    n_hi = float(n_hi)
    if n_hi <= n_lo:
        raise ValueError("slab n_hi must be greater than n_lo")
    phase = np.mod(np.angle(mask), 2.0 * np.pi)
    n_map = n_lo + (n_hi - n_lo) * (phase / (2.0 * np.pi))
    depth = 2.0 * np.pi * (n_hi - n_lo) * d / lam
    meta = {
        "encoding": "full_2pi",
        "n_lo": n_lo,
        "n_hi": n_hi,
        "slab_thickness": d,
        "wavelength": lam,
        "phase_depth_rad": float(depth),
    }
    return np.asarray(n_map, dtype=np.float64), meta


def _soft_disk_index(
    n_map: NDArray,
    x: NDArray,
    y: NDArray,
    *,
    w0: float,
    inner: float,
    n_vac: float = 1.0,
) -> NDArray[np.float64]:
    """Full 2π helix on a disk; raised-cosine taper to vacuum so the square cell is dark."""
    rho = np.sqrt(np.asarray(x, dtype=float) ** 2 + np.asarray(y, dtype=float) ** 2)
    outer = inner + max(0.5 * float(w0), 0.4)
    t = np.ones_like(rho, dtype=float)
    ring = (rho > inner) & (rho < outer)
    t = np.where(rho >= outer, 0.0, t)
    span = max(outer - inner, 1e-9)
    t = np.where(ring, 0.5 * (1.0 + np.cos(np.pi * (rho - inner) / span)), t)
    return np.asarray(n_vac + (np.asarray(n_map, dtype=float) - n_vac) * t, dtype=np.float64)


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
        grid_size: int = 32,
        w0: float = 1.0,
        extent: float = 4.0,
        resolution: int = 12,
        **kwargs: Any,
    ) -> FullWaveResult:
        import meep as mp  # type: ignore

        # Opt-in FDTD. Default off so `pytest` stays fast even if Meep is present.
        if os.environ.get("VQC_MEEP_RUN", "").lower() not in {"1", "true", "yes"}:
            raise FullWaveUnavailable(
                "Meep is installed. Set VQC_MEEP_RUN=1 to run FDTD "
                "(spiral / binary grating / trajectoid reference cells)."
            )

        x, y = cartesian_grid(int(grid_size), float(extent))
        mask = structure.to_phase_mask((x, y), float(wavelength_nm))
        layout = str(kwargs.get("layout") or "source_imprint")
        if layout != "thin_plate_3d":
            return self._run_meep_source_imprint(
                mp,
                structure,
                x,
                y,
                mask,
                L_max=int(L_max),
                w0=float(w0),
                extent=float(extent),
                resolution=int(resolution),
                grid_size=int(grid_size),
                pml=float(kwargs.get("pml", 0.5)),
                sz=float(kwargs.get("sz", 3.6)),
                until=float(kwargs.get("until", 20)),
            )
        ny, nx = mask.shape
        res = int(resolution)
        sx = sy = _snap_cell(2.0 * float(extent), res)
        w0 = float(w0)
        # Affordable charge-correct plate: Ex, n(x,y) function, d=0.7λ, Δn·d=λ.
        if kwargs.get("slab_thickness") is None:
            d = 0.7
        else:
            d = float(kwargs["slab_thickness"])
        lam = 1.0
        encoding = str(kwargs.get("slab_encoding") or "full_2pi")
        n_map, slab_meta = phase_to_slab_index(
            mask,
            thickness=d,
            wavelength=lam,
            n_lo=float(kwargs.get("slab_n_lo", 1.0)),
            n_hi=None if kwargs.get("slab_n_hi") is None else float(kwargs["slab_n_hi"]),
            encoding=encoding,
            n0=float(kwargs.get("slab_n0", 1.0)),
            dn_amp=float(kwargs.get("slab_dn", 0.4)),
        )
        d = float(slab_meta["slab_thickness"])
        n_map = _soft_disk_index(n_map, x, y, w0=w0, inner=float(kwargs.get("slab_radius", 1.7 * w0)))
        profile = str(kwargs.get("slab_profile") or "index")
        n_glass = float(kwargs.get("slab_n", 1.5))
        height_weights = None
        if profile == "height":
            # Geometric SPP: constant-n ramp, h(φ) = d · φ/2π, n·d = λ.
            d = float(lam / n_glass)
            slab_meta["slab_thickness"] = d
            slab_meta["slab_profile"] = "height"
            slab_meta["n_glass"] = n_glass
            slab_meta["phase_depth_rad"] = float(2.0 * np.pi * n_glass * d / lam)
            phase = np.mod(np.angle(mask), 2.0 * np.pi)
            rho = np.sqrt(x**2 + y**2)
            inner = float(kwargs.get("slab_radius", 1.7 * w0))
            outer = inner + max(0.5 * w0, 0.4)
            tap = np.ones_like(rho)
            ring = (rho > inner) & (rho < outer)
            tap = np.where(rho >= outer, 0.0, tap)
            tap = np.where(
                ring,
                0.5 * (1.0 + np.cos(np.pi * (rho - inner) / max(outer - inner, 1e-9))),
                tap,
            )
            h = d * (phase / (2.0 * np.pi)) * tap
            nz = max(6, int(round(d * res)))
            height_weights = np.zeros((nx, ny, nz), dtype=np.float64)
            dz = d / nz
            h_xy = np.ascontiguousarray(h.T)  # (x, y) for Meep
            for iz in range(nz):
                height_weights[:, :, iz] = (h_xy >= (iz + 0.5) * dz).astype(np.float64)
            eps_min, eps_max = 1.0, n_glass**2
            weights_mg = height_weights
        else:
            eps = n_map**2
            eps_min = float(np.min(eps))
            eps_max = float(np.max(eps))
            weights = np.clip((eps - eps_min) / max(eps_max - eps_min, 1e-9), 0.0, 1.0)
            weights_mg = np.ascontiguousarray(weights.T.astype(np.float64))
            slab_meta["slab_profile"] = "index"
        pml = float(kwargs.get("pml", 1.0))
        sz = _snap_cell(float(kwargs.get("sz", 6.0)), res)
        until = float(kwargs.get("until", 40))
        # Source in vacuum; monitor just downstream of the plate (near-field helix).
        z_src = -min(1.2, sz / 2.0 - pml - 0.25)
        z_mon = 0.5 * d + 0.35
        if z_mon > sz / 2.0 - pml - 0.2:
            z_mon = sz / 2.0 - pml - 0.2
        from scipy.interpolate import RegularGridInterpolator

        n_interp = RegularGridInterpolator(
            (np.asarray(y[:, 0], dtype=float), np.asarray(x[0, :], dtype=float)),
            n_map,
            bounds_error=False,
            fill_value=1.0,
        )

        def _amp(p):
            return float(np.exp(-(p.x**2 + p.y**2) / max(w0**2, 1e-6)))

        def _mat(p):
            return mp.Medium(index=float(n_interp((p.y, p.x))))

        use_func = profile != "height" and str(kwargs.get("slab_material") or "function") != "grid"
        # Transverse Ex: z-propagating paraxial field (Ez is longitudinal).
        pol = str(kwargs.get("component") or "Ex")
        src_comp = getattr(mp, pol)
        dft_comp = src_comp

        try:
            if use_func:
                plate_mat: Any = _mat
            else:
                gz = int(weights_mg.shape[2]) if weights_mg.ndim == 3 else 1
                plate_mat = mp.MaterialGrid(
                    grid_size=mp.Vector3(nx, ny, gz),
                    medium1=mp.Medium(epsilon=eps_min),
                    medium2=mp.Medium(epsilon=eps_max),
                    weights=weights_mg,
                    do_averaging=profile != "height",
                )
            geom = [
                mp.Block(
                    center=mp.Vector3(0, 0, 0),
                    size=mp.Vector3(sx, sy, d),
                    material=plate_mat,
                )
            ]
            src = [
                mp.Source(
                    mp.GaussianSource(frequency=1.0 / lam, width=2.0),
                    component=src_comp,
                    center=mp.Vector3(0, 0, z_src),
                    size=mp.Vector3(sx * 0.9, sy * 0.9, 0),
                    amp_func=_amp,
                )
            ]
            sim = mp.Simulation(
                cell_size=mp.Vector3(sx, sy, sz),
                geometry=geom,
                sources=src,
                resolution=int(resolution),
                boundary_layers=[mp.PML(pml)],
                dimensions=3,
                eps_averaging=False,
            )
            dft_vol = mp.Volume(center=mp.Vector3(0, 0, z_mon), size=mp.Vector3(sx, sy, 0))
            dft = sim.add_dft_fields([dft_comp], 1.0 / lam, 1.0 / lam, 1, where=dft_vol)
            sim.run(until=until)
            ez = np.array(sim.get_dft_array(dft, dft_comp, 0), dtype=np.complex128)
        except Exception as exc:
            raise FullWaveUnavailable(f"Meep FDTD run failed: {exc}") from exc

        if ez.ndim == 1:
            raise FullWaveUnavailable("Meep returned a 1-D Ez array; expected a 2-D plane.")
        field = _resample_complex(np.transpose(np.asarray(ez, dtype=np.complex128)), x.shape)
        return pack_oam_result(
            field,
            x,
            y,
            L_max=int(L_max),
            w0=w0,
            backend="meep",
            extras=_meep_run_meta(
                layout="thin_plate_3d",
                resolution=res,
                cell=(sx, sy, sz),
                grid_size=int(nx),
                extent=float(extent),
                pml=pml,
                z_src=z_src,
                z_mon=z_mon,
                kind=structure.kind,
                meep_version=getattr(mp, "__version__", None),
                extra={
                    "until": until,
                    "slab_material": "function" if use_func else "grid",
                    "component": pol,
                    **slab_meta,
                },
            ),
        )

    def _run_meep_source_imprint(
        self,
        mp,
        structure: Structure,
        x: NDArray,
        y: NDArray,
        mask: NDArray[np.complex128],
        *,
        L_max: int,
        w0: float,
        extent: float,
        resolution: int,
        grid_size: int,
        pml: float = 0.5,
        sz: float = 3.6,
        until: float = 20,
    ) -> FullWaveResult:
        """Vacuum 3-D FDTD whose source is Gaussian × thin-element mask.

        This is the Meep validation path that conserves OAM: the plate is
        applied as a complex source, then Ez is DFT-monitored downstream.
        A resolved dielectric slab is ``layout=thin_plate_3d``.
        """
        from scipy.interpolate import RegularGridInterpolator

        res = int(resolution)
        sx = sy = _snap_cell(2.0 * float(extent), res)
        sz = _snap_cell(float(sz), res)
        pml = float(pml)
        z_src = -min(0.7, sz / 2.0 - pml - 0.15)
        z_mon = -z_src
        lam = 1.0
        field0 = gaussian_beam(x, y, w0=w0) * mask
        x_ax = np.asarray(x[0, :], dtype=float)
        y_ax = np.asarray(y[:, 0], dtype=float)
        interp = RegularGridInterpolator(
            (y_ax, x_ax),
            field0,
            bounds_error=False,
            fill_value=0.0,
        )

        def _amp(p):
            val = interp((p.y, p.x))
            return complex(val)

        try:
            src = [
                mp.Source(
                    mp.GaussianSource(frequency=1.0 / lam, width=2.0),
                    component=mp.Ez,
                    center=mp.Vector3(0, 0, z_src),
                    size=mp.Vector3(sx * 0.95, sy * 0.95, 0),
                    amp_func=_amp,
                )
            ]
            sim = mp.Simulation(
                cell_size=mp.Vector3(sx, sy, sz),
                geometry=[],
                sources=src,
                resolution=int(resolution),
                boundary_layers=[mp.PML(pml)],
                dimensions=3,
            )
            dft_vol = mp.Volume(center=mp.Vector3(0, 0, z_mon), size=mp.Vector3(sx, sy, 0))
            dft = sim.add_dft_fields([mp.Ez], 1.0 / lam, 1.0 / lam, 1, where=dft_vol)
            sim.run(until=float(until))
            ez = np.array(sim.get_dft_array(dft, mp.Ez, 0), dtype=np.complex128)
        except Exception as trans_exc:
            raise FullWaveUnavailable(f"Meep FDTD run failed: {trans_exc}") from trans_exc

        if ez.ndim == 1:
            raise FullWaveUnavailable("Meep DFT returned a 1-D array; expected a 2-D plane.")
        # Meep DFT arrays are (x, y); workbench grids are (y, x).
        field = _resample_complex(np.transpose(ez), x.shape)
        return pack_oam_result(
            field,
            x,
            y,
            L_max=int(L_max),
            w0=w0,
            backend="meep",
            extras=_meep_run_meta(
                layout="source_imprint",
                resolution=res,
                cell=(sx, sy, sz),
                grid_size=int(grid_size),
                extent=float(extent),
                pml=pml,
                z_src=z_src,
                z_mon=z_mon,
                kind=structure.kind,
                meep_version=getattr(mp, "__version__", None),
                extra={"until": float(until)},
            ),
        )


def _snap_cell(size: float, resolution: int) -> float:
    """Round a Meep cell length so volume is an integer number of pixels."""
    res = int(resolution)
    return float(round(float(size) * res) / res)


def _meep_run_meta(
    *,
    layout: str,
    resolution: int,
    cell: tuple[float, float, float],
    grid_size: int,
    extent: float,
    pml: float,
    z_src: float,
    z_mon: float,
    kind: str,
    meep_version: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sx, sy, sz = cell
    meta = {
        "layout": layout,
        "resolution": int(resolution),
        "cell_size": {"sx": sx, "sy": sy, "sz": sz},
        "n_pixels": {
            "nx": int(round(sx * resolution)),
            "ny": int(round(sy * resolution)),
            "nz": int(round(sz * resolution)),
        },
        "grid_size": int(grid_size),
        "extent": float(extent),
        "pml": float(pml),
        "z_src": float(z_src),
        "z_mon": float(z_mon),
        "kind": kind,
        "meep_version": meep_version,
    }
    if extra:
        meta.update(extra)
    return meta


def _resample_complex(src: NDArray[np.complex128], shape: tuple[int, int]) -> NDArray[np.complex128]:
    """Nearest-neighbor resample of a 2-D field onto ``shape``."""
    ny, nx = int(shape[0]), int(shape[1])
    sy, sx = src.shape[:2]
    yi = np.linspace(0, sy - 1, ny).astype(int)
    xi = np.linspace(0, sx - 1, nx).astype(int)
    return src[yi][:, xi]


class RCWABackend(FullWaveBackend):
    """Periodic layer-stack RCWA. Tries ``grcwa`` then ``nannos``."""

    name = "rcwa"

    def run(self, structure: Structure, **kwargs: Any) -> FullWaveResult:
        from vqc_workbench.simulation.lg import gaussian_beam
        from vqc_workbench.simulation.rcwa import run_grcwa, run_nannos, structure_to_stack

        engines: list[str] = []
        for mod in ("grcwa", "nannos"):
            try:
                __import__(mod)
                engines.append(mod)
            except ImportError:
                continue
        if not engines:
            raise FullWaveUnavailable(
                "No RCWA engine found (tried grcwa, nannos). Use backend='scalar' "
                "or `pip install grcwa` / `pip install nannos`."
            )
        L_max = int(kwargs.get("L_max", 8))
        wavelength_nm = float(kwargs.get("wavelength_nm", 1550.0))
        grid_size = int(kwargs.get("grid_size", 32))
        w0 = float(kwargs.get("w0", 1.0))
        extent = float(kwargs.get("extent", 4.0))
        nG = int(kwargs.get("nG", 21))
        n_hi = float(kwargs.get("n_hi", 1.5))
        n_lo = float(kwargs.get("n_lo", 1.0))
        slab_thickness = kwargs.get("slab_thickness")
        stack = structure_to_stack(
            structure,
            wavelength_nm=wavelength_nm,
            grid_size=grid_size,
            extent=extent,
            nG=nG,
            n_hi=n_hi,
            n_lo=n_lo,
            slab_thickness=None if slab_thickness is None else float(slab_thickness),
        )
        x, y = cartesian_grid(int(grid_size), float(extent))
        last_err: Exception | None = None
        field = None
        meta: dict[str, Any] = {}
        prefer = str(kwargs.get("engine") or engines[0])
        order = [prefer] + [e for e in engines if e != prefer]
        for name in order:
            try:
                if name == "grcwa":
                    field, meta = run_grcwa(stack, x=x, y=y)
                else:
                    field, meta = run_nannos(stack, x=x, y=y)
                break
            except Exception as exc:
                last_err = exc
                continue
        if field is None:
            raise FullWaveUnavailable(f"RCWA layer-stack solve failed: {last_err}") from last_err
        envelope = gaussian_beam(x, y, w0=w0)
        transmitted = np.asarray(field, dtype=np.complex128) * envelope
        extras = {
            "layout": "layer_stack",
            "wavelength_nm": wavelength_nm,
            "L_max": L_max,
            "grid_size": grid_size,
            "extent": extent,
            "period_x": stack.period_x,
            "period_y": stack.period_y,
            "nG": stack.nG,
            "note": (
                "RCWA layer stack (superstrate / patterned slab / substrate) "
                "under planewave illumination; OAM from the reconstructed "
                "transmitted field × Gaussian envelope."
            ),
        }
        extras.update(stack.extras)
        extras.update(meta)
        return pack_oam_result(
            transmitted,
            x,
            y,
            L_max=L_max,
            w0=w0,
            backend="rcwa",
            extras=extras,
        )


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
