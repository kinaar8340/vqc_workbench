"""Bind a ladder document to Workbench(): modes, frames, spectrum, scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.ladder.frames import RGB, axial_for_stage, st_for_stage
from vqc_workbench.ladder.model import LadderDocument, Rung
from vqc_workbench.simulation.modal import ModeResult


@dataclass
class SpectrumReadout:
    node_id: str
    node_name: str
    axis: str  # ell | wavelength_nm
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    peak: float
    peak_label: str
    fwhm: float
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "axis": self.axis,
            "x": self.x.tolist(),
            "y": self.y.tolist(),
            "peak": self.peak,
            "peak_label": self.peak_label,
            "fwhm": self.fwhm,
            "extras": self.extras,
        }


@dataclass
class RungState:
    rung_id: str
    modes: ModeResult | None
    expected_ell: int | None
    dominant_ell: int | None
    axial: RGB
    spatiotemporal: RGB
    kind: str
    params: dict[str, Any]
    alarm: str = ""


@dataclass
class LadderRuntime:
    doc: LadderDocument
    rungs: dict[str, RungState] = field(default_factory=dict)
    spectrum: SpectrumReadout | None = None


def _fwhm(x: NDArray, y: NDArray) -> float:
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    if y.size < 2:
        return 0.0
    peak = float(np.max(y))
    if peak <= 0:
        return 0.0
    half = peak * 0.5
    above = y >= half
    if not np.any(above):
        return 0.0
    i0, i1 = int(np.argmax(above)), int(len(above) - 1 - np.argmax(above[::-1]))
    return float(abs(x[i1] - x[i0]))


class LadderEngine:
    """Evaluate a ladder against the live Workbench façade."""

    def __init__(self, workbench: Any | None = None, grid_size: int | None = None):
        self._wb = workbench
        self.grid_size = grid_size

    @property
    def wb(self):
        if self._wb is None:
            from vqc_workbench.api import Workbench

            self._wb = Workbench()
        return self._wb

    def bind(self, doc: LadderDocument) -> LadderRuntime:
        runtime = LadderRuntime(doc=doc)
        n = int(self.grid_size or doc.grid_size)
        frame_u = (int(doc.frame_index) % max(1, int(doc.n_pulse_frames))) / max(
            1, int(doc.n_pulse_frames)
        )
        alarms: list[str] = []
        for rung in doc.rungs:
            state = self._eval_rung(doc, rung, n=n, frame_u=frame_u)
            runtime.rungs[rung.id] = state
            if state.alarm:
                alarms.append(state.alarm)
        doc.alarm = "; ".join(alarms)
        runtime.spectrum = self.spectrum_for(doc, runtime, doc.selected_node_id)
        return runtime

    def tick(self, doc: LadderDocument) -> None:
        if doc.scan_active:
            doc.cycle = int(doc.cycle) + 1
            self.step_frame(doc, 1)

    def _eval_rung(self, doc: LadderDocument, rung: Rung, n: int, frame_u: float) -> RungState:
        spec = dict(rung.workbench or {})
        kind = str(spec.get("kind", "identity"))
        params = dict(spec.get("params") or {})
        modes: ModeResult | None = None
        expected = None
        dominant = None
        alarm = ""
        try:
            structure = self.wb.create_structure(kind, **params)
            forecast = self.wb.forecast_charge(structure)
            expected = forecast.expected_ell
            modes = self.wb.simulate_modes(
                structure,
                L_max=int(doc.L_max),
                grid_size=n,
                wavelength_nm=float(doc.wavelength_nm),
            )
            dominant = modes.dominant_ell()
            if expected is not None and dominant != expected:
                alarm = f"{rung.title}: peak ell={dominant:+d} != forecast {expected:+d}"
        except Exception as exc:  # live bench: keep HMI up if a kind fails
            alarm = f"{rung.title}: {type(exc).__name__}"

        ell = int(params.get("ell", 1) or 1)
        layers = 3
        for c in rung.contacts:
            if c.kind == "param" and c.tag in {"TWIST", "LAYERS"} and c.value:
                try:
                    layers = int(c.value)
                except ValueError:
                    pass
            if c.kind == "param" and c.tag == "ELL_SET" and c.value:
                try:
                    ell = int(c.value)
                except ValueError:
                    pass
        if dominant is not None and kind != "identity":
            ell = int(dominant) if dominant != 0 else ell

        field = None if modes is None else modes.field
        mask = None if modes is None else modes.phase_mask
        x = None if modes is None else modes.x
        y = None if modes is None else modes.y
        axial = axial_for_stage(
            rung.stage,
            field=field,
            phase_mask=mask,
            x=x,
            y=y,
            ell=ell,
            layers=layers,
            frame=frame_u,
            n=n,
        )
        st = st_for_stage(rung.stage, ell=ell, layers=layers, frame=frame_u, n=n)
        return RungState(
            rung_id=rung.id,
            modes=modes,
            expected_ell=expected,
            dominant_ell=dominant,
            axial=axial,
            spatiotemporal=st,
            kind=kind,
            params=params,
            alarm=alarm,
        )

    def spectrum_for(
        self,
        doc: LadderDocument,
        runtime: LadderRuntime,
        node_id: str | None,
    ) -> SpectrumReadout:
        if not node_id:
            return SpectrumReadout(
                node_id="",
                node_name="(no selection)",
                axis="ell",
                x=np.arange(-doc.L_max, doc.L_max + 1, dtype=np.float64),
                y=np.zeros(2 * doc.L_max + 1, dtype=np.float64),
                peak=0.0,
                peak_label="—",
                fwhm=0.0,
            )
        rung = doc.node_rung(node_id)
        local = node_id.split(".", 1)[-1]
        name = doc.node_label(node_id)
        state = None if rung is None else runtime.rungs.get(rung.id)

        if rung is not None and local in {"laser"}:
            wl = np.linspace(480.0, 590.0, 128)
            y = np.exp(-((wl - float(doc.wavelength_nm)) ** 2) / (2 * 4.5**2))
            return SpectrumReadout(
                node_id=node_id,
                node_name=name,
                axis="wavelength_nm",
                x=wl,
                y=y,
                peak=float(doc.wavelength_nm),
                peak_label=f"λ={doc.wavelength_nm:.0f} nm",
                fwhm=_fwhm(wl, y),
            )

        if state is not None and state.modes is not None:
            modes = state.modes
            y = np.asarray(modes.intensity, dtype=np.float64)
            x = np.asarray(modes.ell, dtype=np.float64)
            peak_ell = int(modes.dominant_ell())
            return SpectrumReadout(
                node_id=node_id,
                node_name=name,
                axis="ell",
                x=x,
                y=y,
                peak=float(peak_ell),
                peak_label=f"ell={peak_ell:+d}",
                fwhm=_fwhm(x, y),
                extras={
                    "expectation_ell": float(modes.expectation_ell()),
                    "expected_ell": state.expected_ell,
                    "kind": state.kind,
                },
            )

        x = np.arange(-doc.L_max, doc.L_max + 1, dtype=np.float64)
        return SpectrumReadout(
            node_id=node_id,
            node_name=name,
            axis="ell",
            x=x,
            y=np.zeros_like(x),
            peak=0.0,
            peak_label="—",
            fwhm=0.0,
        )

    def step_frame(self, doc: LadderDocument, delta: int = 1) -> None:
        n = max(1, int(doc.n_pulse_frames))
        doc.frame_index = int(doc.frame_index + delta) % n

    def call_workbench(self, doc: LadderDocument, action: str, node_id: str | None = None) -> Any:
        """Optional HITL / export / VQC actions from a selected tag."""
        rung = doc.node_rung(node_id or doc.selected_node_id or "")
        if rung is None:
            raise KeyError("no rung for action")
        spec = dict(rung.workbench or {})
        kind = str(spec.get("kind", "identity"))
        params = dict(spec.get("params") or {})
        structure = self.wb.create_structure(kind, **params)
        if action == "simulate":
            return self.wb.simulate_modes(structure, L_max=doc.L_max, grid_size=doc.grid_size)
        if action == "export-slm":
            from pathlib import Path

            out = Path("outputs/ladder_slm_phase.npy")
            return self.wb.export_slm(structure, out)
        if action == "run-vqc":
            return self.wb.run_vqc(structure, b"Hi", L_max=doc.L_max, compensate=kind != "identity")
        if action == "hitl":
            return self.wb.hitl("Hi", structure, channel="projector")
        raise ValueError(f"unknown workbench action {action!r}")
