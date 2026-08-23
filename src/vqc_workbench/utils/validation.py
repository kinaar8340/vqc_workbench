"""Small numeric guards."""

from __future__ import annotations


def require_positive(name: str, value: float) -> float:
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return value
