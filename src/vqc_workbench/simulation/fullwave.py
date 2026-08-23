"""Optional Meep / RCWA backends. Modal path is always available; these are opt-in."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FullWaveUnavailable(RuntimeError):
    pass


class FullWaveBackend(ABC):
    name: str = "fullwave"

    @abstractmethod
    def run(self, geometry: dict[str, Any], sources: Any = None, monitors: Any = None) -> dict[str, Any]:
        ...


class MeepBackend(FullWaveBackend):
    """FDTD backend. Requires ``meep`` (not installed by default)."""

    name = "meep"

    def run(self, geometry: dict[str, Any], sources: Any = None, monitors: Any = None) -> dict[str, Any]:
        try:
            import meep as mp  # type: ignore
        except ImportError as exc:
            raise FullWaveUnavailable(
                "Meep is not installed. Install MIT Meep and `pip install vqc-workbench[fullwave]`, "
                "or stay on the modal backend (default)."
            ) from exc
        # Minimal 2-D cell: geometry_dict is the structure's to_geometry_dict().
        sx = float(geometry.get("sx", 8.0))
        sy = float(geometry.get("sy", 8.0))
        resolution = int(geometry.get("resolution", 20))
        cell = mp.Vector3(sx, sy, 0)
        sim = mp.Simulation(cell_size=cell, resolution=resolution, sources=[], geometry=[])
        # Do not run a heavy FDTD in the default constructor path; return a handle.
        return {
            "backend": "meep",
            "cell": (sx, sy),
            "resolution": resolution,
            "geometry": geometry,
            "note": "skeleton: populate sources/geometry then sim.run(...)",
            "simulation": sim,
        }


class RCWABackend(FullWaveBackend):
    """Periodic grating / metasurface backend. Tries ``grcwa`` then ``nannos``."""

    name = "rcwa"

    def run(self, geometry: dict[str, Any], sources: Any = None, monitors: Any = None) -> dict[str, Any]:
        engine = None
        for mod in ("grcwa", "nannos"):
            try:
                engine = __import__(mod)
                break
            except ImportError:
                continue
        if engine is None:
            raise FullWaveUnavailable(
                "No RCWA engine found (tried grcwa, nannos). Stay on the modal backend "
                "or install an RCWA package."
            )
        return {
            "backend": "rcwa",
            "engine": engine.__name__,
            "geometry": geometry,
            "note": "skeleton: map grating params to RCWA layers / Fourier orders",
        }


def get_backend(name: str) -> FullWaveBackend:
    key = name.lower().strip()
    if key in {"meep", "fdtd"}:
        return MeepBackend()
    if key in {"rcwa", "grcwa", "nannos"}:
        return RCWABackend()
    raise KeyError(f"unknown full-wave backend {name!r}")
