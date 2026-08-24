"""High-level façade: Workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from vqc_workbench.adapters import EcosystemStatus, probe_ecosystem
from vqc_workbench.core.config import WorkbenchConfig, load_config
from vqc_workbench.core.materials import MaterialLibrary
from vqc_workbench.core.registry import available_kinds, get_structure_class, structure_from_spec
from vqc_workbench.core.structure import Structure
from vqc_workbench.export.hologram import export_hologram_stack
from vqc_workbench.export.slm import export_slm
from vqc_workbench.simulation.compare import compare_many, compare_spectra
from vqc_workbench.simulation.fullwave import FullWaveEngine, FullWaveResult
from vqc_workbench.simulation.inverse import InverseDesigner, InverseResult
from vqc_workbench.simulation.hitl import HITLResult, run_hitl
from vqc_workbench.simulation.lattice import LatticeCouplingResult, couple_modes_to_lattice
from vqc_workbench.simulation.metrics import PipelineResult
from vqc_workbench.simulation.modal import ModalSimulator, ModeResult
from vqc_workbench.simulation.pipeline import VQCPipeline
from vqc_workbench.structures.cascade import Cascade, MatchedFilter, compensate_structure
from vqc_workbench.structures.charge import ChargeForecast, forecast_charge
from vqc_workbench.utils.io import load_yaml

# Ensure structure kinds are registered.
import vqc_workbench.structures  # noqa: F401


class Workbench:
    """Main entry point for interactive or scripted use."""

    def __init__(self, config_path: str | Path | None = None):
        self.config: WorkbenchConfig = load_config(config_path)
        self.materials = MaterialLibrary()
        self.modal = ModalSimulator(self.config)
        self.pipeline = VQCPipeline(
            self.modal,
            qec_level=self.config.qec_reps,
            use_bmgl=self.config.use_bmgl,
            config=self.config,
        )
        self.ecosystem: EcosystemStatus = probe_ecosystem()
        self.fullwave = FullWaveEngine(modal=self.modal)

    def kinds(self) -> list[str]:
        return available_kinds()

    def create_structure(self, kind: str, name: str | None = None, **params: Any) -> Structure:
        cls = get_structure_class(kind)
        material = self.materials.get(params.pop("material", None), default=self.config.default_material)
        return cls(name=name or kind, params=params, material=material)

    def create_grating(self, kind: str = "spiral_phase", **params: Any) -> Structure:
        aliases = {
            "spiral_phase": "spiral_phase",
            "spiral": "spiral_phase",
            "binary": "binary_grating",
            "binary_grating": "binary_grating",
            "blazed": "blazed_grating",
            "blazed_grating": "blazed_grating",
            "forked": "forked_hologram",
            "forked_hologram": "forked_hologram",
        }
        return self.create_structure(aliases.get(kind, kind), **params)

    def create_orbital_braille(self, n_orbs: int = 4, **params: Any) -> Structure:
        params.setdefault("n_orbs", n_orbs)
        return self.create_structure("orbital_braille", **params)

    def create_trajectoid(self, payload_hash: str | None = None, **params: Any) -> Structure:
        """Analytic Jacobi–Anger trenches, or ``live=True`` for generate_shell."""
        if payload_hash is not None:
            params["payload_hash"] = payload_hash
        return self.create_structure("trajectoid", **params)

    def create_metasurface(
        self,
        phase_func: Callable | Any = None,
        **params: Any,
    ) -> Structure:
        if phase_func is not None:
            params["phase_func"] = phase_func
        return self.create_structure("metasurface", **params)

    def create_flux_lattice(self, **params: Any) -> Structure:
        return self.create_structure("flux_lattice", **params)

    def load_structure(self, path: str | Path) -> Structure:
        spec = load_yaml(path)
        return structure_from_spec(spec, materials=self.materials)

    def matched_filter(self, structure: Structure) -> MatchedFilter:
        return MatchedFilter(target=structure)

    def cascade(self, *stages: Structure, name: str = "cascade") -> Cascade:
        return Cascade(name=name, stages=list(stages))

    def compensate(self, structure: Structure) -> Cascade:
        """Structure followed by its inverse thin-element (≈ identity)."""
        return compensate_structure(structure)

    def forecast_charge(self, structure: Structure) -> ChargeForecast:
        return forecast_charge(structure)

    def simulate_modes(self, structure: Structure, **kwargs: Any) -> ModeResult:
        return self.modal.structure_to_modes(structure, **kwargs)

    def simulate_fullwave(
        self,
        structure: Structure,
        backend: str = "scalar",
        **kwargs: Any,
    ) -> FullWaveResult:
        kwargs.setdefault("L_max", self.config.L_max)
        kwargs.setdefault("wavelength_nm", self.config.wavelength_nm)
        kwargs.setdefault("grid_size", self.config.grid_size)
        kwargs.setdefault("w0", self.config.w0)
        kwargs.setdefault("extent", self.config.extent)
        return self.fullwave.run(structure, backend=backend, **kwargs)

    def compare_backends(
        self,
        structure: Structure,
        backends: tuple[str, ...] = ("modal", "scalar"),
        **kwargs: Any,
    ) -> dict[str, Any]:
        names = tuple(backends)
        if len(names) < 2:
            raise ValueError("compare_backends needs at least two backend names")
        results = [self.simulate_fullwave(structure, backend=name, **kwargs) for name in names]
        if len(results) == 2:
            return compare_spectra(results[0], results[1])
        return compare_many(results)

    def run_vqc(self, structure: Structure, payload: Any, **kwargs: Any) -> PipelineResult:
        return self.pipeline.run(structure, payload, **kwargs)

    def couple_to_lattice(
        self,
        source: Structure | ModeResult,
        *,
        kappa: float = 0.85,
        steps: int = 8,
        ell: int | None = None,
        nx: int = 12,
        kick_strength: float = 0.08,
        flywheel_sites: int = 4,
        sweep_kappa: list[float] | tuple[float, ...] | None = None,
        L_max: int | None = None,
        grid_size: int | None = None,
    ) -> LatticeCouplingResult:
        """Deposit OAM flux from a structure or mode snapshot onto a Hopf lattice."""
        if isinstance(source, ModeResult):
            modes = source
        else:
            modes = self.simulate_modes(
                source,
                L_max=L_max or self.config.L_max,
                grid_size=grid_size or min(self.config.grid_size, 64),
            )
        return couple_modes_to_lattice(
            modes,
            self.modal,
            kappa=kappa,
            steps=steps,
            ell=ell,
            nx=nx,
            kick_strength=kick_strength,
            flywheel_sites=flywheel_sites,
            sweep_kappa=list(sweep_kappa) if sweep_kappa is not None else None,
            w0=self.config.w0,
            wavelength_nm=self.config.wavelength_nm,
        )

    def inverse_design(
        self,
        kind: str,
        *,
        objective: str = "charge",
        target_ell: int | None = None,
        payload: bytes | str = b"Hi",
        compensate: bool = False,
        param_names: list[str] | None = None,
        seed_params: dict[str, Any] | None = None,
        L_max: int | None = None,
        grid_size: int | None = None,
        max_evals: int = 256,
    ) -> InverseResult:
        """Search structure parameters for a target charge or VQC fidelity."""
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        designer = InverseDesigner(
            self,
            L_max=int(L_max or self.config.L_max),
            grid_size=int(grid_size or min(self.config.grid_size, 64)),
            max_evals=int(max_evals),
        )
        return designer.optimize(
            kind,
            objective=objective,  # type: ignore[arg-type]
            target_ell=target_ell,
            payload=payload,
            compensate=compensate,
            param_names=param_names,
            seed_params=seed_params,
        )

    def hitl(
        self,
        payload: bytes | str = "I live in Oregon",
        structure: Structure | None = None,
        *,
        device: str | None = None,
        channel: str = "projector",
        n_frames: int = 8,
        out: str | Path | None = None,
        full: bool = False,
        capture: str | Path | None = None,
        n_orbs: int = 4,
        grid_size: int | None = None,
    ) -> HITLResult:
        """SLM playlist plus vqc_demo projector-proxy loopback (or a capture decode)."""
        return run_hitl(
            payload,
            structure,
            device=device or self.config.slm_device,
            channel=channel,
            n_frames=n_frames,
            out=out,
            full=full,
            capture=capture,
            n_orbs=n_orbs,
            wavelength_nm=self.config.wavelength_nm,
            grid_size=grid_size,
        )

    def export_slm(
        self,
        structure: Structure,
        path: str | Path,
        device: str | None = None,
        wavelength_nm: float | None = None,
    ) -> Path:
        return export_slm(
            structure,
            path,
            device=device or self.config.slm_device,
            wavelength_nm=wavelength_nm or self.config.wavelength_nm,
        )

    def export_hologram_stack(
        self,
        structure: Structure,
        out_dir: str | Path,
        n_frames: int = 8,
        device: str | None = None,
    ) -> Path:
        return export_hologram_stack(
            structure,
            out_dir,
            n_frames=n_frames,
            device=device or self.config.slm_device,
            wavelength_nm=self.config.wavelength_nm,
        )

    def launch_dashboard(self, port: int = 8501) -> None:
        from vqc_workbench.ui.dashboard import launch_dashboard

        launch_dashboard(port=port)
