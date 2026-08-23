"""Side-by-side comparison of modal vs full-wave OAM spectra."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.simulation.fullwave import FullWaveResult


def _aligned_intensity(
    ell_a: NDArray,
    i_a: NDArray,
    ell_b: NDArray,
    i_b: NDArray,
) -> tuple[NDArray[np.int64], NDArray[np.float64], NDArray[np.float64]]:
    ells = np.union1d(np.asarray(ell_a, dtype=np.int64), np.asarray(ell_b, dtype=np.int64)).astype(np.int64)
    va = np.zeros(ells.size, dtype=np.float64)
    vb = np.zeros(ells.size, dtype=np.float64)
    lookup_a = {int(e): float(v) for e, v in zip(ell_a, i_a)}
    lookup_b = {int(e): float(v) for e, v in zip(ell_b, i_b)}
    for i, e in enumerate(ells):
        va[i] = lookup_a.get(int(e), 0.0)
        vb[i] = lookup_b.get(int(e), 0.0)
    return ells, va, vb


def intensity_cosine(a: FullWaveResult, b: FullWaveResult) -> float:
    _ells, va, vb = _aligned_intensity(a.ell, a.intensity, b.ell, b.intensity)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def compare_spectra(a: FullWaveResult, b: FullWaveResult) -> dict[str, Any]:
    """Return cosine similarity, L1 distance, and dominant-ℓ agreement."""
    ells, va, vb = _aligned_intensity(a.ell, a.intensity, b.ell, b.intensity)
    l1 = float(np.sum(np.abs(va - vb)))
    return {
        "backend_a": a.backend,
        "backend_b": b.backend,
        "cosine": intensity_cosine(a, b),
        "l1": l1,
        "dominant_ell_a": a.dominant_ell(),
        "dominant_ell_b": b.dominant_ell(),
        "dominant_match": a.dominant_ell() == b.dominant_ell(),
        "expectation_ell_a": a.expectation_ell(),
        "expectation_ell_b": b.expectation_ell(),
        "cached_a": a.cached,
        "cached_b": b.cached,
        "ell": ells,
        "intensity_a": va,
        "intensity_b": vb,
    }
