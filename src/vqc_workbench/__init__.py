"""VQC Photonic Workbench — structure editor, modal OAM engine, conduit pipeline."""

from __future__ import annotations

from vqc_workbench.api import Workbench
from vqc_workbench.core.materials import Material, MaterialLibrary
from vqc_workbench.core.structure import ParametricCell, Structure
from vqc_workbench.simulation.fullwave import FullWaveResult, FullWaveUnavailable
from vqc_workbench.simulation.inverse import InverseResult
from vqc_workbench.simulation.lattice import LatticeCouplingResult, LatticeUnavailable
from vqc_workbench.simulation.metrics import PipelineResult
from vqc_workbench.simulation.modal import ModalSimulator, ModeResult, PropagationResult

__version__ = "0.3.0"

__all__ = [
    "Workbench",
    "Structure",
    "ParametricCell",
    "Material",
    "MaterialLibrary",
    "ModalSimulator",
    "ModeResult",
    "PropagationResult",
    "PipelineResult",
    "FullWaveResult",
    "FullWaveUnavailable",
    "InverseResult",
    "LatticeCouplingResult",
    "LatticeUnavailable",
    "__version__",
]
