"""Simulation backends and the end-to-end VQC pipeline."""

from vqc_workbench.simulation.compare import compare_many, compare_spectra
from vqc_workbench.simulation.fullwave import (
    FullWaveEngine,
    FullWaveResult,
    FullWaveUnavailable,
)
from vqc_workbench.simulation.metrics import PipelineResult, oam_purity
from vqc_workbench.simulation.modal import ModalSimulator, ModeResult, PropagationResult
from vqc_workbench.simulation.inverse import InverseDesigner, InverseResult
from vqc_workbench.simulation.pipeline import VQCPipeline

__all__ = [
    "ModalSimulator",
    "ModeResult",
    "PropagationResult",
    "VQCPipeline",
    "PipelineResult",
    "oam_purity",
    "FullWaveEngine",
    "FullWaveResult",
    "FullWaveUnavailable",
    "compare_spectra",
    "compare_many",
    "InverseDesigner",
    "InverseResult",
]
