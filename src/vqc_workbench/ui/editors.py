"""Default parameter schemas for structure forms."""

from __future__ import annotations

from typing import Any

SCHEMAS: dict[str, list[dict[str, Any]]] = {
    "spiral_phase": [
        {"name": "ell", "type": "int", "min": -16, "max": 16, "default": 3},
        {"name": "radius_mm", "type": "float", "min": 0.1, "max": 20.0, "default": 5.0},
    ],
    "binary_grating": [
        {"name": "period", "type": "float", "min": 0.05, "max": 4.0, "default": 0.4},
        {"name": "duty", "type": "float", "min": 0.05, "max": 0.95, "default": 0.5},
        {"name": "depth_rad", "type": "float", "min": 0.0, "max": 6.28, "default": 3.14},
        {"name": "angle_deg", "type": "float", "min": 0.0, "max": 180.0, "default": 0.0},
    ],
    "blazed_grating": [
        {"name": "period", "type": "float", "min": 0.05, "max": 4.0, "default": 0.5},
        {"name": "depth_rad", "type": "float", "min": 0.0, "max": 12.56, "default": 6.28},
        {"name": "angle_deg", "type": "float", "min": 0.0, "max": 180.0, "default": 0.0},
    ],
    "forked_hologram": [
        {"name": "ell", "type": "int", "min": -16, "max": 16, "default": 1},
        {"name": "period", "type": "float", "min": 0.05, "max": 4.0, "default": 0.35},
        {"name": "angle_deg", "type": "float", "min": 0.0, "max": 180.0, "default": 0.0},
    ],
    "orbital_braille": [
        {"name": "n_orbs", "type": "int", "min": 1, "max": 8, "default": 4},
        {"name": "t_frac", "type": "float", "min": 0.0, "max": 1.0, "default": 0.35},
    ],
    "trajectoid": [
        {"name": "n_trenches", "type": "int", "min": 2, "max": 32, "default": 8},
        {"name": "winding", "type": "int", "min": 1, "max": 8, "default": 2},
    ],
    "flux_lattice": [
        {"name": "ell", "type": "int", "min": -8, "max": 8, "default": 3},
        {"name": "n_sites", "type": "int", "min": 2, "max": 24, "default": 8},
        {"name": "kappa", "type": "float", "min": 0.5, "max": 1.2, "default": 0.85},
    ],
    "metasurface": [
        {"name": "ell_target", "type": "int", "min": -16, "max": 16, "default": 1},
        {"name": "fill_factor", "type": "float", "min": 0.1, "max": 1.0, "default": 1.0},
    ],
    "identity": [],
}


def schema_for(kind: str) -> list[dict[str, Any]]:
    return list(SCHEMAS.get(kind, []))
