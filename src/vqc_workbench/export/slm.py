"""Phase-only SLM export (Holoeye / Meadowlark / Thorlabs presets).

Mirrors vqc_proto / vqc_demo / flux_trajectoid device tables so packages
from this workbench load on the same hardware path.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import Structure
from vqc_workbench.utils.grid import cartesian_grid
from vqc_workbench.utils.io import ensure_dir

SLM_PRESETS: dict[str, dict[str, Any]] = {
    "generic_512": {
        "name": "generic_512",
        "width": 512,
        "height": 512,
        "pitch_um": 8.0,
        "wavelength_nm": 1550.0,
        "bit_depth": 8,
        "notes": "Algorithm validation grid.",
    },
    "holoeye_pluto_2": {
        "name": "holoeye_pluto_2",
        "width": 1920,
        "height": 1080,
        "pitch_um": 8.0,
        "wavelength_nm": 1550.0,
        "bit_depth": 8,
        "notes": "Holoeye PLUTO-2 class. Upload 8-bit BMP/PNG.",
    },
    "meadowlark_512": {
        "name": "meadowlark_512",
        "width": 512,
        "height": 512,
        "pitch_um": 15.0,
        "wavelength_nm": 1550.0,
        "bit_depth": 16,
        "notes": "Meadowlark 512×512 (16-bit phase).",
    },
    "thorlabs_1080p": {
        "name": "thorlabs_1080p",
        "width": 1920,
        "height": 1080,
        "pitch_um": 6.4,
        "wavelength_nm": 633.0,
        "bit_depth": 8,
        "notes": "Visible HeNe demo on a 1080p LCOS.",
    },
}


@dataclass
class SLMConfig:
    name: str = "generic_512"
    width: int = 512
    height: int = 512
    pitch_um: float = 8.0
    wavelength_nm: float = 1550.0
    bit_depth: int = 8
    extent_mm: float = 4.0
    notes: str = ""

    @classmethod
    def from_preset(cls, name: str, extent_mm: float = 4.0) -> SLMConfig:
        if name not in SLM_PRESETS:
            known = ", ".join(sorted(SLM_PRESETS))
            raise KeyError(f"unknown SLM preset {name!r}; choose one of: {known}")
        p = SLM_PRESETS[name]
        return cls(
            name=p["name"],
            width=int(p["width"]),
            height=int(p["height"]),
            pitch_um=float(p["pitch_um"]),
            wavelength_nm=float(p["wavelength_nm"]),
            bit_depth=int(p["bit_depth"]),
            extent_mm=extent_mm,
            notes=str(p.get("notes", "")),
        )


def phase_to_levels(phase: NDArray, bit_depth: int = 8) -> NDArray[np.uint16]:
    wrapped = np.mod(np.angle(phase) if np.iscomplexobj(phase) else np.asarray(phase), 2 * np.pi)
    max_level = (1 << bit_depth) - 1
    levels = np.rint(wrapped / (2 * np.pi) * max_level).astype(np.uint16)
    return levels


def export_slm(
    structure: Structure,
    path: str | Path,
    device: str = "generic_512",
    wavelength_nm: float = 1550.0,
    extent_mm: float | None = None,
) -> Path:
    cfg = SLMConfig.from_preset(device, extent_mm=extent_mm or 4.0)
    n = max(cfg.width, cfg.height)
    # Square compute grid; crop/pad to device later if needed.
    half = cfg.extent_mm / 2.0
    x, y = cartesian_grid(n=min(n, 512), extent=half)
    mask = structure.to_phase_mask((x, y), wavelength_nm=cfg.wavelength_nm or wavelength_nm)
    levels = phase_to_levels(mask, bit_depth=cfg.bit_depth)

    out = Path(path)
    if out.suffix == "":
        ensure_dir(out)
        npy_path = out / "slm_phase.npy"
        levels_path = out / "phase_levels.npy"
        manifest_path = out / "manifest.json"
    else:
        ensure_dir(out.parent)
        npy_path = out
        levels_path = out.with_name(out.stem + "_levels.npy")
        manifest_path = out.with_name(out.stem + "_manifest.json")

    np.save(npy_path, mask)
    np.save(levels_path, levels)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "device": asdict(cfg),
        "structure": structure.summarize(),
        "phase_npy": str(npy_path),
        "levels_npy": str(levels_path),
        "generator": "vqc_workbench.export.slm",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    try:
        from PIL import Image

        vis = (levels * (255.0 / max((1 << cfg.bit_depth) - 1, 1))).astype(np.uint8)
        png = npy_path.with_suffix(".png") if npy_path.suffix == ".npy" else Path(str(npy_path) + ".png")
        Image.fromarray(vis).save(png)
    except Exception:
        pass
    return npy_path
