"""Reversible OAM-bit payload codec with repetition QEC.

``flux_hopf_lib.encode_shard`` is a quaternion *fingerprint* (not invertible
for arbitrary bytes). The workbench therefore packs payload bits into a
ladder of OAM mode amplitudes, repeats them ``qec_reps`` times, and recovers
by majority vote after propagation.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.geometry import Quaternion, encode_shard


def payload_to_bytes(payload: bytes | str | np.ndarray) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    arr = np.asarray(payload)
    return arr.astype(np.uint8).tobytes()


def _bits_from_bytes(data: bytes) -> NDArray[np.uint8]:
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.uint8)


def _bytes_from_bits(bits: NDArray[np.uint8], n_bytes: int) -> bytes:
    padded = np.zeros(n_bytes * 8, dtype=np.uint8)
    n = min(bits.size, padded.size)
    padded[:n] = bits[:n]
    return np.packbits(padded).tobytes()[:n_bytes]


def repeat_bits(bits: NDArray[np.uint8], reps: int) -> NDArray[np.uint8]:
    reps = max(int(reps), 1)
    if reps == 1:
        return bits
    return np.repeat(bits, reps)


def majority_decode(coded: NDArray[np.uint8], reps: int) -> NDArray[np.uint8]:
    reps = max(int(reps), 1)
    if reps == 1:
        return coded
    n = (coded.size // reps) * reps
    block = coded[:n].reshape(-1, reps)
    return (block.mean(axis=1) >= 0.5).astype(np.uint8)


def capacity_bits(L_max: int, bits_per_mode: int = 2) -> int:
    """Usable payload bits on ℓ ∈ [-L_max, L_max] \\ {0}."""
    return int(bits_per_mode) * 2 * int(L_max)


def min_L_max(n_bits: int, bits_per_mode: int = 2) -> int:
    n_modes = int(np.ceil(max(int(n_bits), 1) / float(bits_per_mode)))
    return max(2, (n_modes + 1) // 2)


def bits_to_coefficients(
    bits: NDArray[np.uint8],
    L_max: int,
    scale: float = 1.0,
) -> dict[int, complex]:
    """Pack two bits per mode: amplitude bit + phase bit (ℓ=0 is a reference tone)."""
    ells = [e for e in range(-L_max, L_max + 1) if e != 0]
    weights: dict[int, complex] = {0: complex(scale * 0.35)}
    for i, ell in enumerate(ells):
        ia = 2 * i
        ip = 2 * i + 1
        bit_a = int(bits[ia]) if ia < bits.size else 0
        bit_p = int(bits[ip]) if ip < bits.size else 0
        amp = (0.90 if bit_a else 0.18) * scale
        phase = 0.0 if bit_p else np.pi
        weights[ell] = amp * np.exp(1j * phase)
    return weights


def coefficients_to_bits(
    weights: dict[int, complex],
    n_bits: int,
    L_max: int,
) -> NDArray[np.uint8]:
    ells = [e for e in range(-L_max, L_max + 1) if e != 0]
    mags = np.array([abs(weights.get(e, 0.0)) for e in ells], dtype=float)
    phases = np.array([np.angle(weights.get(e, 0.0)) for e in ells], dtype=float)
    if mags.size == 0:
        return np.zeros(n_bits, dtype=np.uint8)
    thresh = 0.5 * (float(mags.max()) + float(mags.min()))
    amp_bits = (mags >= thresh).astype(np.uint8)
    # Phase near 0 → 1, near ±π → 0
    phase_bits = (np.abs(np.angle(np.exp(1j * phases))) < (np.pi / 2)).astype(np.uint8)
    packed = np.empty(amp_bits.size * 2, dtype=np.uint8)
    packed[0::2] = amp_bits
    packed[1::2] = phase_bits
    out = np.zeros(n_bits, dtype=np.uint8)
    n = min(n_bits, packed.size)
    out[:n] = packed[:n]
    return out


def encode_payload(
    payload: bytes,
    L_max: int,
    qec_reps: int = 3,
) -> tuple[dict[int, complex], Quaternion, int]:
    bits = _bits_from_bytes(payload)
    coded = repeat_bits(bits, qec_reps)
    weights = bits_to_coefficients(coded, L_max=L_max)
    q = encode_shard(payload)
    return weights, q, int(coded.size)


def decode_payload(
    weights: dict[int, complex],
    n_payload_bytes: int,
    L_max: int,
    qec_reps: int = 3,
) -> bytes:
    n_bits = n_payload_bytes * 8 * max(int(qec_reps), 1)
    coded = coefficients_to_bits(weights, n_bits=n_bits, L_max=L_max)
    decoded = majority_decode(coded, qec_reps)
    return _bytes_from_bits(decoded, n_payload_bytes)


def bmgl_inhibit(turbulence: float, gamma: float = 1.5) -> float:
    """p-wave BMGL-style inhibition of an effective turbulence scale."""
    gamma = max(float(gamma), 1.0)
    return float(turbulence) / gamma
