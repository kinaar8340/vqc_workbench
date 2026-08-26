"""Editable photonic ladder: rungs, contacts, coils-as-monitors, lab mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from vqc_workbench.core.config import workbench_root
from vqc_workbench.utils.io import dump_yaml, load_yaml

SELECT_GLOW = "#00FF00"
LADDER_SCHEMA = 1


def default_ladder_path() -> Path:
    return workbench_root() / "configs" / "ladders" / "beam_evolution.yaml"


@dataclass
class Contact:
    """Ladder contact / tag. Classic NO / NC / trigger / parameter."""

    id: str
    tag: str
    kind: str = "NO"  # NO | NC | trigger | param
    closed: bool = True
    label: str = ""
    value: str = ""
    help: str = ""

    def node_id(self, rung_id: str) -> str:
        return f"{rung_id}.{self.id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tag": self.tag,
            "kind": self.kind,
            "closed": self.closed,
            "label": self.label,
            "value": self.value,
            "help": self.help,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Contact:
        return cls(
            id=str(data["id"]),
            tag=str(data.get("tag", data["id"])).upper(),
            kind=str(data.get("kind", "NO")),
            closed=bool(data.get("closed", True)),
            label=str(data.get("label", "")),
            value=str(data.get("value", "")),
            help=str(data.get("help", "")),
        )


@dataclass
class BeamMonitor:
    """Live beam-state display that replaces a PLC coil."""

    id: str
    view: str  # axial | spatiotemporal
    title: str
    scale: str = "INTENSITY"
    frame_ids: list[int] = field(default_factory=list)
    help: str = ""

    def node_id(self, rung_id: str) -> str:
        return f"{rung_id}.{self.id}"

    def frame_label(self) -> str:
        if not self.frame_ids:
            return ""
        lo, hi = min(self.frame_ids), max(self.frame_ids)
        if lo == hi:
            return f"FR {lo}"
        return f"FR {lo}–{hi}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "view": self.view,
            "title": self.title,
            "scale": self.scale,
            "frame_ids": list(self.frame_ids),
            "help": self.help,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BeamMonitor:
        frames = [int(x) for x in data.get("frame_ids", [])]
        return cls(
            id=str(data["id"]),
            view=str(data.get("view", "axial")),
            title=str(data.get("title", "MONITOR")),
            scale=str(data.get("scale", "INTENSITY")),
            frame_ids=frames,
            help=str(data.get("help", "")),
        )


@dataclass
class EquipmentDevice:
    """Physical optical-bench component under a logic rung."""

    id: str
    tag: str
    name: str
    kind: str
    signal: bool = True
    help: str = ""

    def node_id(self, rung_id: str) -> str:
        return f"{rung_id}.{self.id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tag": self.tag,
            "name": self.name,
            "kind": self.kind,
            "signal": self.signal,
            "help": self.help,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EquipmentDevice:
        tag = str(data.get("tag", data["id"]))
        if not tag.startswith("["):
            tag = f"[{tag}]"
        return cls(
            id=str(data["id"]),
            tag=tag,
            name=str(data.get("name", data["id"])),
            kind=str(data.get("kind", "device")),
            signal=bool(data.get("signal", True)),
            help=str(data.get("help", "")),
        )


@dataclass
class Rung:
    """One sequential beam-evolution stage + its lab mapping row."""

    id: str
    number: int
    title: str
    stage: str
    subtitle: str = ""
    contacts: list[Contact] = field(default_factory=list)
    axial: BeamMonitor | None = None
    spatiotemporal: BeamMonitor | None = None
    equipment: list[EquipmentDevice] = field(default_factory=list)
    workbench: dict[str, Any] = field(default_factory=dict)
    help: str = ""

    def node_ids(self) -> list[str]:
        ids = [f"{self.id}.rail_l", f"{self.id}.rail_r"]
        for c in self.contacts:
            ids.append(c.node_id(self.id))
        if self.axial:
            ids.append(self.axial.node_id(self.id))
        if self.spatiotemporal:
            ids.append(self.spatiotemporal.node_id(self.id))
        for d in self.equipment:
            ids.append(d.node_id(self.id))
        return ids

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "stage": self.stage,
            "subtitle": self.subtitle,
            "contacts": [c.as_dict() for c in self.contacts],
            "axial": None if self.axial is None else self.axial.as_dict(),
            "spatiotemporal": None if self.spatiotemporal is None else self.spatiotemporal.as_dict(),
            "equipment": [d.as_dict() for d in self.equipment],
            "workbench": dict(self.workbench),
            "help": self.help,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rung:
        axial = data.get("axial")
        st = data.get("spatiotemporal")
        return cls(
            id=str(data["id"]),
            number=int(data.get("number", 0)),
            title=str(data.get("title", "")),
            stage=str(data.get("stage", "initial")),
            subtitle=str(data.get("subtitle", "")),
            contacts=[Contact.from_dict(c) for c in data.get("contacts", [])],
            axial=None if not axial else BeamMonitor.from_dict(axial),
            spatiotemporal=None if not st else BeamMonitor.from_dict(st),
            equipment=[EquipmentDevice.from_dict(d) for d in data.get("equipment", [])],
            workbench=dict(data.get("workbench") or {}),
            help=str(data.get("help", "")),
        )


@dataclass
class LadderDocument:
    """Full ladder program: title/status, spectrum selection, stacked rungs."""

    title: str = "Photonic Ladder Diagram – Beam Evolution + Lab Mapping"
    version: str = "0.3.0"
    schema: int = LADDER_SCHEMA
    wavelength_nm: float = 532.0
    L_max: int = 8
    grid_size: int = 64
    scan_active: bool = True
    edit_mode: bool = True
    cycle: int = 0
    selected_node_id: str | None = None
    glow_until_trigger: bool = True
    n_pulse_frames: int = 16
    frame_index: int = 0
    alarm: str = ""
    rungs: list[Rung] = field(default_factory=list)

    def all_node_ids(self) -> list[str]:
        ids: list[str] = []
        for rung in self.rungs:
            ids.extend(rung.node_ids())
        return ids

    def find_rung(self, rung_id: str) -> Rung | None:
        for rung in self.rungs:
            if rung.id == rung_id:
                return rung
        return None

    def node_rung(self, node_id: str) -> Rung | None:
        prefix = node_id.split(".", 1)[0]
        return self.find_rung(prefix)

    def node_label(self, node_id: str) -> str:
        if not node_id:
            return "(none)"
        rung = self.node_rung(node_id)
        if rung is None:
            return node_id
        local = node_id.split(".", 1)[-1]
        for c in rung.contacts:
            if c.id == local:
                return c.tag
        for d in rung.equipment:
            if d.id == local:
                return d.tag
        if rung.axial and rung.axial.id == local:
            return rung.axial.title
        if rung.spatiotemporal and rung.spatiotemporal.id == local:
            return rung.spatiotemporal.title
        if local in {"rail_l", "rail_r"}:
            return f"{rung.title} RAIL"
        return node_id

    def select(self, node_id: str | None) -> None:
        """Persist a single-node selection. Glow stays until trigger or reselect."""
        if node_id is None:
            self.selected_node_id = None
            return
        if node_id not in self.all_node_ids():
            raise KeyError(f"unknown ladder node {node_id!r}")
        self.selected_node_id = node_id

    def trigger(self, node_id: str) -> None:
        """Fire a node. Clears glow if this node was selected."""
        rung = self.node_rung(node_id)
        if rung is None:
            return
        local = node_id.split(".", 1)[-1]
        for c in rung.contacts:
            if c.id == local:
                c.closed = not c.closed
                break
        if self.glow_until_trigger and self.selected_node_id == node_id:
            self.selected_node_id = None

    def add_rung(self, rung: Rung | None = None, after: int | None = None) -> Rung:
        n = len(self.rungs) + 1
        if rung is None:
            rid = f"rung{n}"
            while self.find_rung(rid) is not None:
                n += 1
                rid = f"rung{n}"
            rung = _blank_rung(rid, n)
        if after is None:
            self.rungs.append(rung)
        else:
            self.rungs.insert(int(after) + 1, rung)
        self._renumber()
        return rung

    def delete_rung(self, rung_id: str) -> None:
        self.rungs = [r for r in self.rungs if r.id != rung_id]
        if self.selected_node_id and self.selected_node_id.startswith(rung_id + "."):
            self.selected_node_id = None
        self._renumber()

    def move_rung(self, rung_id: str, delta: int) -> None:
        idx = next((i for i, r in enumerate(self.rungs) if r.id == rung_id), None)
        if idx is None:
            return
        j = idx + int(delta)
        if not (0 <= j < len(self.rungs)):
            return
        self.rungs[idx], self.rungs[j] = self.rungs[j], self.rungs[idx]
        self._renumber()

    def _renumber(self) -> None:
        for i, rung in enumerate(self.rungs, start=1):
            rung.number = i

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "title": self.title,
            "version": self.version,
            "wavelength_nm": self.wavelength_nm,
            "L_max": self.L_max,
            "grid_size": self.grid_size,
            "scan_active": self.scan_active,
            "edit_mode": self.edit_mode,
            "cycle": self.cycle,
            "selected_node_id": self.selected_node_id,
            "glow_until_trigger": self.glow_until_trigger,
            "n_pulse_frames": self.n_pulse_frames,
            "frame_index": self.frame_index,
            "alarm": self.alarm,
            "rungs": [r.as_dict() for r in self.rungs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LadderDocument:
        return cls(
            title=str(data.get("title", cls.title)),
            version=str(data.get("version", cls.version)),
            schema=int(data.get("schema", LADDER_SCHEMA)),
            wavelength_nm=float(data.get("wavelength_nm", 532.0)),
            L_max=int(data.get("L_max", 8)),
            grid_size=int(data.get("grid_size", 64)),
            scan_active=bool(data.get("scan_active", True)),
            edit_mode=bool(data.get("edit_mode", True)),
            cycle=int(data.get("cycle", 0)),
            selected_node_id=data.get("selected_node_id"),
            glow_until_trigger=bool(data.get("glow_until_trigger", True)),
            n_pulse_frames=int(data.get("n_pulse_frames", 16)),
            frame_index=int(data.get("frame_index", 0)),
            alarm=str(data.get("alarm", "")),
            rungs=[Rung.from_dict(r) for r in data.get("rungs", [])],
        )


def load_ladder(path: str | Path) -> LadderDocument:
    return LadderDocument.from_dict(load_yaml(path))


def save_ladder(doc: LadderDocument, path: str | Path) -> Path:
    return dump_yaml(doc.as_dict(), path)


def _blank_rung(rung_id: str, number: int) -> Rung:
    return Rung(
        id=rung_id,
        number=number,
        title="NEW STAGE",
        stage="initial",
        subtitle="identity",
        contacts=[
            Contact(id="enable", tag="ENABLE", kind="NO", closed=True),
        ],
        axial=BeamMonitor(
            id="axial",
            view="axial",
            title="AXIAL / PHASE-FRONT",
            scale="INTENSITY",
            frame_ids=[1],
        ),
        spatiotemporal=BeamMonitor(
            id="st",
            view="spatiotemporal",
            title="SPATIOTEMPORAL / LENGTH",
            scale="INTENSITY",
            frame_ids=[2],
        ),
        equipment=[
            EquipmentDevice(id="dev", tag="[DEV_01]", name="Unassigned", kind="device"),
        ],
        workbench={"kind": "identity", "params": {}},
    )


def beam_evolution_ladder() -> LadderDocument:
    """Four-rung lab ladder matching the VQC Prototype pulsed-beam sequence."""
    path = default_ladder_path()
    if path.is_file():
        return load_ladder(path)
    return _builtin_beam_evolution()


def _builtin_beam_evolution() -> LadderDocument:
    from vqc_workbench import __version__

    return LadderDocument(
        title="Photonic Ladder Diagram – Beam Evolution + Lab Mapping",
        version=__version__,
        wavelength_nm=532.0,
        selected_node_id="rung1.pulse_in",
        rungs=[
            Rung(
                id="rung1",
                number=1,
                title="INITIAL",
                stage="initial",
                subtitle="Collimated pulse",
                help="Frames 1–3 axial collimated rainbow pulse; frames 4–5 elongated pulse streak.",
                contacts=[
                    Contact(id="pulse_in", tag="PULSE_IN", kind="NO", closed=True, help="Input pulse trigger"),
                    Contact(id="shutter", tag="SHUTTER", kind="NO", closed=True, help="Laser shutter interlock"),
                    Contact(id="trig_532", tag="TRIG_532", kind="trigger", closed=True, help="532 nm fire"),
                ],
                axial=BeamMonitor(
                    id="axial",
                    view="axial",
                    title="AXIAL / PHASE-FRONT",
                    scale="INTENSITY",
                    frame_ids=[1, 2, 3],
                    help="Transverse intensity of the collimated pulse.",
                ),
                spatiotemporal=BeamMonitor(
                    id="st",
                    view="spatiotemporal",
                    title="SPATIOTEMPORAL / LENGTH",
                    scale="INTENSITY",
                    frame_ids=[4, 5],
                    help="Longitudinal pulse streak.",
                ),
                equipment=[
                    EquipmentDevice(id="laser", tag="[LASER_532]", name="532 nm Laser", kind="laser"),
                    EquipmentDevice(id="expander", tag="[BE_01]", name="Beam Expander", kind="expander"),
                    EquipmentDevice(id="dice", tag="[DICE_01]", name="Object Dice Stage", kind="stage"),
                    EquipmentDevice(id="l1", tag="[L1]", name="Lens L1", kind="lens"),
                    EquipmentDevice(id="iris", tag="[IRIS_01]", name="Iris", kind="iris"),
                ],
                workbench={"kind": "identity", "params": {}},
            ),
            Rung(
                id="rung2",
                number=2,
                title="SLM STAGE",
                stage="slm",
                subtitle="Quaternion spiral mask",
                help="Axial vortex / quaternion spiral phase mask + helical vortex propagation length.",
                contacts=[
                    Contact(id="slm_en", tag="SLM_EN", kind="NO", closed=True, help="SLM enable"),
                    Contact(id="hwp_in", tag="HWP_IN", kind="NO", closed=True, help="Half-wave plate in beam"),
                    Contact(id="phase_ld", tag="PHASE_LD", kind="trigger", closed=True, help="Load phase playlist"),
                    Contact(id="ell_set", tag="ELL_SET", kind="param", closed=True, value="1", help="Topological charge"),
                ],
                axial=BeamMonitor(
                    id="axial",
                    view="axial",
                    title="AXIAL / PHASE-FRONT",
                    scale="PHASE",
                    frame_ids=[6, 7, 8],
                    help="Spiral phase mask on the SLM.",
                ),
                spatiotemporal=BeamMonitor(
                    id="st",
                    view="spatiotemporal",
                    title="SPATIOTEMPORAL / LENGTH",
                    scale="INTENSITY",
                    frame_ids=[9, 10],
                    help="Helical vortex along z.",
                ),
                equipment=[
                    EquipmentDevice(id="slm", tag="[SLM_01]", name="SLM", kind="slm"),
                    EquipmentDevice(id="hwp", tag="[HWP_01]", name="HWP (λ/2)", kind="hwp"),
                    EquipmentDevice(id="l3", tag="[L3]", name="Lens L3", kind="lens"),
                    EquipmentDevice(id="gpd", tag="[GPD_01]", name="GPD", kind="detector"),
                ],
                workbench={"kind": "spiral_phase", "params": {"ell": 1}},
            ),
            Rung(
                id="rung3",
                number=3,
                title="HELICAL FORMATION",
                stage="helical",
                subtitle="Nested helical wavefronts",
                help="Nested concentric helical wavefronts + multi-helical twisted layered tubes.",
                contacts=[
                    Contact(id="diff_en", tag="DIFF_EN", kind="NO", closed=True, help="Rotating diffuser"),
                    Contact(id="lcp_in", tag="LCP_IN", kind="NO", closed=True, help="Left-circular polarizer"),
                    Contact(id="twist", tag="TWIST", kind="param", closed=True, value="3", help="Helical layer count"),
                ],
                axial=BeamMonitor(
                    id="axial",
                    view="axial",
                    title="AXIAL / PHASE-FRONT",
                    scale="INTENSITY",
                    frame_ids=[11, 12],
                    help="Concentric nested helical wavefronts.",
                ),
                spatiotemporal=BeamMonitor(
                    id="st",
                    view="spatiotemporal",
                    title="SPATIOTEMPORAL / LENGTH",
                    scale="INTENSITY",
                    frame_ids=[13],
                    help="Multi-helical twisted layered tubes.",
                ),
                equipment=[
                    EquipmentDevice(id="diffuser", tag="[DIFF_01]", name="Rotating Diffuser", kind="diffuser"),
                    EquipmentDevice(id="l4", tag="[L4]", name="Lens L4", kind="lens"),
                    EquipmentDevice(id="lcp", tag="[LCP_01]", name="LCP", kind="polarizer"),
                ],
                workbench={"kind": "trajectoid", "params": {"n_trenches": 8, "winding": 2, "live": False}},
            ),
            Rung(
                id="rung4",
                number=4,
                title="MULTI-LAYER / DETECTION",
                stage="detect",
                subtitle="Dense helical stack → cameras",
                help="Multi-layer helical dense concentric rings + long nested multi-layer helical beam.",
                contacts=[
                    Contact(id="cam1_en", tag="CAM1_EN", kind="NO", closed=True, help="CCD arm"),
                    Contact(id="cam2_en", tag="CAM2_EN", kind="NO", closed=True, help="EMCCD arm"),
                    Contact(id="fiber_tx", tag="FIBER_TX", kind="NO", closed=True, help="Online transmission fiber"),
                    Contact(id="vqc_go", tag="VQC_GO", kind="trigger", closed=True, help="Push to analysis node"),
                ],
                axial=BeamMonitor(
                    id="axial",
                    view="axial",
                    title="AXIAL / PHASE-FRONT",
                    scale="INTENSITY",
                    frame_ids=[14, 15],
                    help="Dense concentric multi-layer rings.",
                ),
                spatiotemporal=BeamMonitor(
                    id="st",
                    view="spatiotemporal",
                    title="SPATIOTEMPORAL / LENGTH",
                    scale="INTENSITY",
                    frame_ids=[16],
                    help="Long nested multi-layer helical beam.",
                ),
                equipment=[
                    EquipmentDevice(id="cam1", tag="[CAM1]", name="Cam1 (CCD)", kind="camera"),
                    EquipmentDevice(id="cam2", tag="[CAM2]", name="Cam2 (EMCCD)", kind="camera"),
                    EquipmentDevice(id="fiber", tag="[FIBER_01]", name="Online Transmission Fiber Path", kind="fiber"),
                    EquipmentDevice(id="analysis", tag="[NODE_AX]", name="To Analysis Node", kind="node"),
                ],
                workbench={"kind": "spiral_phase", "params": {"ell": 3}},
            ),
        ],
    )


def iter_contacts(doc: LadderDocument) -> Iterable[tuple[Rung, Contact]]:
    for rung in doc.rungs:
        for contact in rung.contacts:
            yield rung, contact
