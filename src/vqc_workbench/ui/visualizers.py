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


def plot_backend_spectra(
    results: list,
    *,
    expected_ell: int | None = None,
    path: str | None = None,
    title: str | None = None,
):
    """Three-column (or N-column) OAM bar chart for modal / scalar / Meep."""
    import matplotlib.pyplot as plt

    n = len(results)
    if n < 1:
        raise ValueError("need at least one FullWaveResult")
    fig, axes = plt.subplots(1, n, figsize=(3.4 * n, 3.6), sharey=True, constrained_layout=True)
    if n == 1:
        axes = [axes]
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756"]
    for ax, result, color in zip(axes, results, colors):
        ell = np.asarray(result.ell)
        intensity = np.asarray(result.intensity)
        ax.bar(ell, intensity, color=color, width=0.8, zorder=2)
        if expected_ell is not None:
            ax.axvline(expected_ell, color="#E45756", ls="--", lw=1.0, zorder=3)
        purity = float(np.sum(intensity**2))
        ax.set_title(
            f"{result.backend}\nℓ = {result.dominant_ell():+d}   P = {purity:.3f}",
            fontsize=11,
        )
        ax.set_xlabel("ℓ")
        ax.set_xlim(int(ell.min()) - 0.5, int(ell.max()) + 0.5)
        ax.grid(True, axis="y", alpha=0.3, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("normalized intensity")
    if expected_ell is not None:
        fig.suptitle(title or f"expected ℓ = {expected_ell:+d}", fontsize=12)
    elif title:
        fig.suptitle(title, fontsize=12)
    if path:
        fig.savefig(path, dpi=160)
    return fig
