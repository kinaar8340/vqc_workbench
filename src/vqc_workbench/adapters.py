"""Runtime discovery of the kinaar8340 photonic / VQC ecosystem.

Workbench imports these packages; they must never import vqc_workbench.
Heavy modules with import-time side effects (e.g. vqc_proto ``photonics.py``)
are not imported here — only cheap availability probes.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _path_exists(*parts: str) -> bool:
    return Path(*parts).exists()


@dataclass
class EcosystemStatus:
    flux_hopf_lib: bool = False
    oam_flux: bool = False
    vqc_proto: bool = False
    vqc_demo: bool = False
    flux_trajectoid: bool = False
    hfb: bool = False
    qga: bool = False
    meep: bool = False
    grcwa: bool = False
    notes: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, bool | dict[str, str]]:
        return {
            "flux_hopf_lib": self.flux_hopf_lib,
            "oam_flux": self.oam_flux,
            "vqc_proto": self.vqc_proto,
            "vqc_demo": self.vqc_demo,
            "flux_trajectoid": self.flux_trajectoid,
            "hfb": self.hfb,
            "qga": self.qga,
            "meep": self.meep,
            "grcwa": self.grcwa,
            "notes": self.notes,
        }


def _checkout(home: Path, *rel: str) -> bool:
    return (home.joinpath(*rel)).exists()


def import_oam_flux():
    """Import oam_flux, adding ~/Projects/oam_flux/src if needed. Raises ImportError."""
    try:
        return importlib.import_module("oam_flux")
    except ImportError:
        src = Path.home() / "Projects" / "oam_flux" / "src"
        if src.is_dir():
            import sys

            path = str(src)
            if path not in sys.path:
                sys.path.insert(0, path)
            return importlib.import_module("oam_flux")
        raise


def probe_ecosystem() -> EcosystemStatus:
    home = Path.home() / "Projects"
    env_proto = os.environ.get("VQC_PROTO_PATH")
    proto_roots = [
        Path(env_proto) if env_proto else None,
        home / "vqc_proto" / "proto",
        home / "vqc_proto" / "space" / "orbital-braille",
    ]
    vqc_proto = False
    for root in proto_roots:
        if root is not None and (root / "orbital_braille" / "lg_modes.py").is_file():
            vqc_proto = True
            break
    if not vqc_proto:
        vqc_proto = _module_available("orbital_braille")

    status = EcosystemStatus(
        flux_hopf_lib=_module_available("flux_hopf_lib")
        or _checkout(home, "flux_hopf_lib", "src", "flux_hopf_lib", "__init__.py"),
        oam_flux=_module_available("oam_flux")
        or _checkout(home, "oam_flux", "src", "oam_flux", "__init__.py"),
        vqc_proto=vqc_proto,
        vqc_demo=_module_available("vqc_demo")
        or _checkout(home, "vqc_demo", "src", "vqc_demo", "__init__.py"),
        flux_trajectoid=_module_available("flux_trajectoid")
        or _checkout(home, "flux_trajectoid", "src", "flux_trajectoid", "__init__.py"),
        hfb=_module_available("hfb") or _checkout(home, "hfb", "hfb", "__init__.py"),
        qga=_path_exists(str(home / "qga" / "lib" / "hopf_lattice.py")),
        meep=_module_available("meep"),
        grcwa=_module_available("grcwa") or _module_available("nannos"),
    )
    if not status.flux_hopf_lib:
        status.notes["flux_hopf_lib"] = "optional; local quaternion fallback in use"
    if not status.meep:
        status.notes["meep"] = "optional FDTD backend not installed; use backend='scalar'"
    if not status.grcwa:
        status.notes["grcwa"] = "optional RCWA backend not installed; use backend='scalar'"
    status.notes["scalar"] = "angular-spectrum full-wave lite is always available"
    return status
