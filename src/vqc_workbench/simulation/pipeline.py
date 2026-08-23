"""End-to-end: encode → structure coupling → propagate → QEC → decode."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from vqc_workbench.core.config import WorkbenchConfig, load_config
from vqc_workbench.core.geometry import encode_shard
from vqc_workbench.core.structure import Structure
from vqc_workbench.simulation.codec import (
    bmgl_inhibit,
    decode_payload,
    encode_payload,
    min_L_max,
    payload_to_bytes,
)
from vqc_workbench.simulation.lg import project_helical_spectrum, synthesize_helical
from vqc_workbench.simulation.metrics import PipelineResult, bit_error_rate, oam_purity
from vqc_workbench.simulation.modal import ModalSimulator, ModeResult


class VQCPipeline:
    def __init__(
        self,
        modal: ModalSimulator | None = None,
        qec_level: int = 1,
        use_bmgl: bool = True,
        config: WorkbenchConfig | None = None,
    ):
        self.config = config or (modal.config if modal is not None else load_config())
        self.modal = modal or ModalSimulator(self.config)
        self.qec_level = int(qec_level)
        self.use_bmgl = bool(use_bmgl)

    def run(
        self,
        structure: Structure,
        payload: bytes | str | np.ndarray,
        **sim_kwargs: Any,
    ) -> PipelineResult:
        t0 = time.perf_counter()
        data = payload_to_bytes(payload)
        qec_reps = int(sim_kwargs.pop("qec_reps", self.qec_level or self.config.qec_reps))
        needed = min_L_max(len(data) * 8 * max(qec_reps, 1))
        requested = sim_kwargs.pop("L_max", None)
        L_max = int(requested if requested is not None else max(self.config.L_max, needed))
        L_max = max(L_max, needed)
        w0 = float(sim_kwargs.pop("w0", self.config.w0))
        wavelength_nm = float(sim_kwargs.pop("wavelength_nm", self.config.wavelength_nm))
        grid_size = int(sim_kwargs.pop("grid_size", self.config.grid_size))
        # Keep the spatial grid fine enough to resolve |ℓ| ~ L_max.
        grid_size = max(grid_size, min(256, 8 * L_max))
        turbulence = float(sim_kwargs.pop("turbulence", self.config.turbulence))
        if self.use_bmgl:
            turbulence = bmgl_inhibit(turbulence, gamma=self.config.bmgl_gamma)
        compensate = bool(sim_kwargs.pop("compensate", False))
        if compensate:
            from vqc_workbench.structures.cascade import compensate_structure

            structure = compensate_structure(structure)

        weights, quat, _n_coded = encode_payload(data, L_max=L_max, qec_reps=qec_reps)
        x, y = self.modal._grid(grid_size)
        tx_field = synthesize_helical(weights, x, y, w0=w0)
        mask = structure.to_phase_mask((x, y), wavelength_nm)
        coupled = tx_field * mask

        coupled_w = project_helical_spectrum(coupled, x, y, L_max=L_max, w0=w0)
        ells = np.arange(-L_max, L_max + 1, dtype=np.int64)
        coeffs = np.array([coupled_w[int(e)] for e in ells], dtype=np.complex128)
        mag2 = np.abs(coeffs) ** 2
        total = float(np.sum(mag2)) or 1.0
        modes = ModeResult(
            ell=ells,
            coefficients=coeffs,
            intensity=mag2 / total,
            phase_mask=mask,
            field=coupled,
            x=x,
            y=y,
            wavelength_nm=wavelength_nm,
            L_max=L_max,
        )
        prop = self.modal.propagate(modes, turbulence=turbulence, **sim_kwargs)
        rx_coeffs = prop.coefficients_z[-1]
        rx_weights = {int(e): complex(c) for e, c in zip(ells, rx_coeffs)}
        recovered = decode_payload(rx_weights, n_payload_bytes=len(data), L_max=L_max, qec_reps=qec_reps)
        rec_q = encode_shard(recovered)
        # Quaternion fidelity via chordal distance on S³ (1 = identical).
        dist = quat.chordal_distance(rec_q)
        fidelity = float(max(0.0, 1.0 - 0.5 * dist**2))
        # Prefer exact payload match as a hard fidelity floor.
        if recovered == data:
            fidelity = max(fidelity, 0.999)
        ber = bit_error_rate(data, recovered)
        purity = oam_purity(rx_coeffs)
        return PipelineResult(
            fidelity=fidelity,
            ber=ber,
            oam_purity=purity,
            recovered_payload=recovered,
            payload=data,
            quaternion=quat,
            recovered_quaternion=rec_q,
            modes=modes,
            propagation=prop,
            metrics={
                "L_max": L_max,
                "qec_reps": qec_reps,
                "turbulence": turbulence,
                "dominant_ell": modes.dominant_ell(),
                "n_bytes": len(data),
                "compensated": compensate,
            },
            timing_s=time.perf_counter() - t0,
        )
