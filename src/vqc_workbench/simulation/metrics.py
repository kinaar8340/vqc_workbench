"""Fidelity, BER, OAM purity, and pipeline result container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.geometry import Quaternion


def oam_purity(coefficients: NDArray) -> float:
    mag2 = np.abs(np.asarray(coefficients)) ** 2
    total = float(np.sum(mag2))
    if total <= 0:
        return 0.0
    p = mag2 / total
    return float(np.sum(p**2))


def bit_error_rate(tx: bytes, rx: bytes) -> float:
    n = 8 * max(len(tx), len(rx), 1)
    a = int.from_bytes(tx.ljust(len(rx), b"\x00"), "big") if tx or rx else 0
    b = int.from_bytes(rx.ljust(len(tx), b"\x00"), "big") if tx or rx else 0
    # Compare over the union length in bits.
    width = 8 * max(len(tx), len(rx), 1)
    xor = a ^ b
    errs = xor.bit_count() if hasattr(int, "bit_count") else bin(xor).count("1")
    return float(errs) / float(width)


@dataclass
class PipelineResult:
    fidelity: float
    ber: float
    oam_purity: float
    recovered_payload: bytes
    payload: bytes
    quaternion: Quaternion
    recovered_quaternion: Quaternion
    modes: Any = None
    propagation: Any = None
    metrics: dict[str, Any] = field(default_factory=dict)
    timing_s: float = 0.0

    @property
    def payload_match(self) -> bool:
        return self.recovered_payload == self.payload

    def summarize(self) -> dict[str, Any]:
        try:
            recovered = self.recovered_payload.decode("utf-8")
        except UnicodeDecodeError:
            recovered = self.recovered_payload.hex()
        return {
            "fidelity": self.fidelity,
            "ber": self.ber,
            "oam_purity": self.oam_purity,
            "payload_match": self.payload_match,
            "recovered_payload": recovered,
            "timing_s": self.timing_s,
            **self.metrics,
        }
