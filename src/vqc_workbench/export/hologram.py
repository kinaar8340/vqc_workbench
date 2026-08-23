"""Hologram stack helper (phase frames for typehead / SLM sequences)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vqc_workbench.core.structure import Structure
from vqc_workbench.export.slm import export_slm
from vqc_workbench.utils.io import ensure_dir


def export_hologram_stack(
    structure: Structure,
    out_dir: str | Path,
    n_frames: int = 8,
    device: str = "generic_512",
    wavelength_nm: float = 1550.0,
) -> Path:
    """Export a short phase-frame stack by sweeping a structure parameter.

    Orbital Braille uses ``t_frac``; other structures get a copy of the single
    mask (still useful as an SLM playlist).
    """
    dest = ensure_dir(out_dir)
    frames = []
    for i in range(max(int(n_frames), 1)):
        t_frac = (i + 0.5) / max(n_frames, 1)
        if "t_frac" in structure.params:
            snap = structure.update(t_frac=t_frac)
        else:
            snap = structure
        path = dest / f"frame_{i:03d}.npy"
        export_slm(snap, path, device=device, wavelength_nm=wavelength_nm)
        frames.append(str(path))
    stack_path = dest / "phase_stack.npy"
    loaded = [np.load(p) for p in frames]
    np.save(stack_path, np.stack(loaded, axis=0))
    return dest
