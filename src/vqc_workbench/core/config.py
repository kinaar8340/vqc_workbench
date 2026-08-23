"""YAML config loading and package-root discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vqc_workbench.utils.io import load_yaml


def workbench_root() -> Path:
    """Return the repo (or install) root that contains ``configs/default.yaml``."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "configs" / "default.yaml").is_file():
            return parent
    return here.parents[3]


def default_config_path() -> Path:
    return workbench_root() / "configs" / "default.yaml"


def _deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


@dataclass
class WorkbenchConfig:
    raw: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    @property
    def backend(self) -> str:
        return str(_deep_get(self.raw, "workbench", "backend", default="modal"))

    @property
    def seed(self) -> int:
        return int(_deep_get(self.raw, "workbench", "seed", default=42))

    @property
    def L_max(self) -> int:
        return int(_deep_get(self.raw, "photonics", "L_max", default=8))

    @property
    def wavelength_nm(self) -> float:
        return float(_deep_get(self.raw, "photonics", "wavelength_nm", default=1550.0))

    @property
    def w0(self) -> float:
        return float(_deep_get(self.raw, "photonics", "w0", default=1.0))

    @property
    def grid_size(self) -> int:
        return int(_deep_get(self.raw, "photonics", "grid_size", default=128))

    @property
    def extent(self) -> float:
        return float(_deep_get(self.raw, "photonics", "extent", default=4.0))

    @property
    def n_z(self) -> int:
        return int(_deep_get(self.raw, "photonics", "n_z", default=40))

    @property
    def z_start(self) -> float:
        return float(_deep_get(self.raw, "photonics", "z_start", default=0.0))

    @property
    def z_end(self) -> float:
        return float(_deep_get(self.raw, "photonics", "z_end", default=5.0))

    @property
    def turbulence(self) -> float:
        return float(_deep_get(self.raw, "photonics", "turbulence", default=0.0))

    @property
    def chirp(self) -> float:
        return float(_deep_get(self.raw, "photonics", "chirp", default=0.0))

    @property
    def qec_suppression(self) -> int:
        return int(_deep_get(self.raw, "photonics", "qec_suppression", default=1))

    @property
    def qec_reps(self) -> int:
        return int(_deep_get(self.raw, "pipeline", "qec_reps", default=3))

    @property
    def use_bmgl(self) -> bool:
        return bool(_deep_get(self.raw, "pipeline", "use_bmgl", default=True))

    @property
    def bmgl_gamma(self) -> float:
        return float(_deep_get(self.raw, "pipeline", "bmgl_gamma", default=1.5))

    @property
    def slm_device(self) -> str:
        return str(_deep_get(self.raw, "export", "device", default="generic_512"))

    @property
    def default_material(self) -> str:
        return str(_deep_get(self.raw, "materials", "default", default="fused_silica"))

    def photonics_dict(self) -> dict[str, Any]:
        return dict(self.raw.get("photonics") or {})

    def merge(self, **overrides: Any) -> WorkbenchConfig:
        """Shallow overlay of photonics/pipeline keys from kwargs."""
        raw = dict(self.raw)
        photonics = dict(raw.get("photonics") or {})
        pipeline = dict(raw.get("pipeline") or {})
        mapping = {
            "L_max": ("photonics", "L_max"),
            "wavelength_nm": ("photonics", "wavelength_nm"),
            "w0": ("photonics", "w0"),
            "grid_size": ("photonics", "grid_size"),
            "extent": ("photonics", "extent"),
            "turbulence": ("photonics", "turbulence"),
            "chirp": ("photonics", "chirp"),
            "n_z": ("photonics", "n_z"),
            "z_end": ("photonics", "z_end"),
            "qec_reps": ("pipeline", "qec_reps"),
            "backend": ("workbench", "backend"),
        }
        workbench = dict(raw.get("workbench") or {})
        for key, value in overrides.items():
            if value is None or key not in mapping:
                continue
            section, name = mapping[key]
            if section == "photonics":
                photonics[name] = value
            elif section == "pipeline":
                pipeline[name] = value
            else:
                workbench[name] = value
        raw["photonics"] = photonics
        raw["pipeline"] = pipeline
        raw["workbench"] = workbench
        return WorkbenchConfig(raw=raw, path=self.path)


def load_config(path: str | Path | None = None) -> WorkbenchConfig:
    cfg_path = Path(path) if path is not None else default_config_path()
    if not cfg_path.is_file():
        return WorkbenchConfig(raw={}, path=None)
    return WorkbenchConfig(raw=load_yaml(cfg_path), path=cfg_path)
