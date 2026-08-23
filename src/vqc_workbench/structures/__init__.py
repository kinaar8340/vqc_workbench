"""Concrete editable structures. Importing this module registers all kinds."""

from vqc_workbench.structures.cascade import Cascade, MatchedFilter, compensate_structure
from vqc_workbench.structures.custom import CustomStructure, IdentityStructure
from vqc_workbench.structures.flux_lattice import FluxLatticeDefect
from vqc_workbench.structures.grating import (
    BinaryGrating,
    BlazedGrating,
    ForkedHologram,
    SpiralPhasePlate,
)
from vqc_workbench.structures.metasurface import Metasurface
from vqc_workbench.structures.orbital_braille import OrbitalBrailleTypehead
from vqc_workbench.structures.trajectoid import TrajectoidShell

__all__ = [
    "SpiralPhasePlate",
    "BinaryGrating",
    "BlazedGrating",
    "ForkedHologram",
    "Metasurface",
    "OrbitalBrailleTypehead",
    "TrajectoidShell",
    "FluxLatticeDefect",
    "CustomStructure",
    "IdentityStructure",
    "Cascade",
    "MatchedFilter",
    "compensate_structure",
]
