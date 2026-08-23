"""Structure → mode coefficients / S-matrix bridge."""

from __future__ import annotations

from typing import Any

import numpy as np

from vqc_workbench.core.structure import Structure
from vqc_workbench.simulation.modal import ModalSimulator, ModeResult


def structure_smatrix_proxy(
    structure: Structure,
    modal: ModalSimulator | None = None,
    L_max: int | None = None,
) -> dict[str, Any]:
    """Thin-element scattering proxy: T = diag(mode amplitudes), R ≈ 0.

    Full-wave backends replace this with a true S-matrix when available.
    """
    modal = modal or ModalSimulator()
    modes: ModeResult = modal.structure_to_modes(structure, L_max=L_max)
    t = modes.coefficients
    n = t.size
    T = np.diag(t)
    R = np.zeros((n, n), dtype=np.complex128)
    S = np.block([[R, T], [T, R]])
    return {
        "ell": modes.ell,
        "T": T,
        "R": R,
        "S": S,
        "transmission": float(np.sum(np.abs(t) ** 2)),
        "kind": structure.kind,
    }
