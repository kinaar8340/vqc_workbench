"""Plotly / matplotlib helpers used by the dashboard and examples."""

from __future__ import annotations

from typing import Any

import numpy as np

from vqc_workbench.simulation.modal import ModeResult, PropagationResult


def mode_bar_data(modes: ModeResult) -> dict[str, Any]:
    return {
        "ell": modes.ell.tolist(),
        "intensity": modes.intensity.tolist(),
        "phase": np.angle(modes.coefficients).tolist(),
    }


def intensity_vs_z(prop: PropagationResult) -> dict[str, Any]:
    return {
        "z": prop.z_steps.tolist(),
        "ells": prop.ells.tolist(),
        "intensity": prop.intensity.tolist(),
    }


def phase_preview(mask: np.ndarray) -> np.ndarray:
    return np.angle(mask)
