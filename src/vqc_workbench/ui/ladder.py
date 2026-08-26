"""Photonic ladder HMI. Launch via ``Workbench.launch_ladder()`` or ``vqc-workbench ladder``."""

from __future__ import annotations

import argparse
import base64
import io
import subprocess
import sys
from pathlib import Path

from vqc_workbench.ladder.model import (
    SELECT_GLOW,
    LadderDocument,
    beam_evolution_ladder,
    list_ladder_presets,
    load_ladder,
    load_ladder_preset,
)

LADDER_CSS = f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: #1a1d21 !important;
  color: #c8ced6;
}}
[data-testid="stHeader"] {{ background: #1a1d21 !important; }}
[data-testid="stToolbar"] {{ display: none; }}
#MainMenu, footer {{ visibility: hidden; }}
section[data-testid="stSidebar"],
[data-testid="stSidebar"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsed"] {{
  display: none !important;
}}
.block-container {{
  padding: 0.25rem 0.55rem 0.8rem 0.55rem;
  max-width: 100%;
}}
.ladder-title, .rung-head, .equip-head, .readout, .help-chip, .ladder-strip {{
  font-family: ui-monospace, "DejaVu Sans Mono", "Consolas", monospace;
}}
.stVerticalBlock {{ gap: 0.22rem !important; }}
[data-testid="stElementContainer"] {{ margin-bottom: 0 !important; }}
.stButton > button {{
  background: #1c2026;
  color: #c8ced6;
  border: 1px solid #4c5360;
  border-radius: 0 !important;
  font-family: ui-monospace, "DejaVu Sans Mono", "Consolas", monospace !important;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.12rem 0.38rem;
  min-height: 1.7rem;
}}
.stButton > button:hover {{
  border-color: {SELECT_GLOW};
  color: {SELECT_GLOW};
}}
div[data-testid="stBaseButton-primary"] > button,
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {{
  background: #0b1a0b !important;
  color: {SELECT_GLOW} !important;
  border: 1px solid {SELECT_GLOW} !important;
  box-shadow: 0 0 8px 1px {SELECT_GLOW} !important;
}}
hr {{ border-color: #4c5360 !important; }}
.ladder-title {{
  background: #1e2228;
  border: 1px solid #4c5360;
  padding: 0.32rem 0.6rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #d5dbe3;
  font-size: 0.88rem;
}}
.ladder-title .status span {{ margin-left: 0.9rem; color: #7d8693; }}
.ladder-title .on {{ color: #3dcc7a; }}
.ladder-strip {{
  background: #23272e;
  border: 1px solid #4c5360;
  border-top: none;
  padding: 0.15rem 0.6rem;
}}
.rung-head, .equip-head {{
  background: #1e2329;
  border: 1px solid #4c5360;
  color: #7d8693;
  font-size: 0.70rem;
  padding: 0.12rem 0.45rem;
  letter-spacing: 0.06em;
}}
.logic-wrap {{
  background: #23272e;
  border: 1px solid #4c5360;
  border-top: none;
  padding: 0.28rem 0.3rem 0.22rem 0.3rem;
}}
.equip-wrap {{
  background: #1f242b;
  border: 1px solid #4c5360;
  border-top: none;
  padding: 0.22rem 0.3rem 0.28rem 0.3rem;
  margin-bottom: 0.35rem;
}}
.mon-bezel {{
  background: #16191d;
  border: 1px solid #4c5360;
  padding: 0.12rem;
}}
.mon-bezel.selected {{
  border: 1px solid {SELECT_GLOW};
  box-shadow: 0 0 8px 1px {SELECT_GLOW};
}}
.mon-cap {{
  color: #7d8693;
  font-size: 0.62rem;
  display: flex;
  justify-content: space-between;
}}
.mon-bezel img {{
  display: block;
  width: 100%;
  height: 108px;
  object-fit: contain;
  background: #0c0e10;
}}
.help-chip {{ color: #7d8693; font-size: 0.70rem; }}
.readout {{
  background: #1c2026;
  border: 1px solid #4c5360;
  padding: 0.35rem 0.5rem;
  font-size: 0.78rem;
  line-height: 1.45;
}}
.rail-bar {{
  width: 4px;
  background: #c5ccd4;
  min-height: 108px;
  margin: 0 auto;
}}
.rail-bar.selected {{
  background: {SELECT_GLOW};
  box-shadow: 0 0 8px 1px {SELECT_GLOW};
}}
</style>
"""


def ladder_script() -> Path:
    return Path(__file__).resolve()


def launch_ladder(port: int = 8502, yaml_path: str | Path | None = None) -> None:
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Streamlit is not installed. `pip install vqc-workbench[ui]` then retry."
        ) from exc
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ladder_script()),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    if yaml_path:
        cmd += ["--", "--yaml", str(yaml_path)]
    raise SystemExit(subprocess.call(cmd))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--yaml", default=None)
    args, _ = p.parse_known_args()
    return args


def _ensure_doc(st, yaml_arg: str | None) -> LadderDocument:
    if "ladder_doc" not in st.session_state:
        if yaml_arg:
            st.session_state.ladder_doc = load_ladder(yaml_arg)
        else:
            st.session_state.ladder_doc = beam_evolution_ladder()
    return st.session_state.ladder_doc


def _select(st, doc: LadderDocument, node_id: str) -> None:
    doc.select(node_id)
    st.session_state.ladder_doc = doc
    st.rerun()


def _png_b64(rgb) -> str:
    from matplotlib.image import imsave

    buf = io.BytesIO()
    imsave(buf, rgb, format="png")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _spectrum_fig(spec) -> "object":
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11.0, 1.35), facecolor="#23272e")
    ax.set_facecolor("#16191d")
    x, y = spec.x, spec.y
    if spec.axis == "ell":
        ax.bar(x, y, width=0.78, color="#3d8a6a", edgecolor="#1e3d32", linewidth=0.4)
        ax.set_xlabel("MODE  ell")
    else:
        ax.plot(x, y, color="#6ec4a8", lw=1.3)
        ax.fill_between(x, y, color="#3d8a6a", alpha=0.35)
        ax.set_xlabel("WAVELENGTH  nm")
    ax.set_ylabel("INT")
    ax.tick_params(colors="#7d8693", labelsize=7)
    ax.xaxis.label.set_color("#7d8693")
    ax.yaxis.label.set_color("#7d8693")
    for spine in ax.spines.values():
        spine.set_color("#4c5360")
    ax.grid(True, axis="y", color="#2e333c", lw=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def _monitor_html(rgb, monitor, selected: bool) -> str:
    klass = "mon-bezel selected" if selected else "mon-bezel"
    title = monitor.title if monitor else "MONITOR"
    flabel = monitor.frame_label() if monitor else ""
    scale = monitor.scale if monitor else ""
    b64 = _png_b64(rgb)
    return (
        f'<div class="{klass}"><div class="mon-cap"><span>{title}</span>'
        f"<span>{flabel}</span></div>"
        f'<img src="data:image/png;base64,{b64}" alt="{title}"/>'
        f'<div class="mon-cap"><span>{scale}</span><span></span></div></div>'
    )


def _program_panel(st, doc: LadderDocument, engine) -> None:
    import yaml

    from vqc_workbench.ladder.export import export_instruction_list

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.caption("PRESET")
        if st.button("LOAD PROTOTYPE SEQUENCE", width="stretch"):
            st.session_state.ladder_doc = load_ladder_preset("beam_evolution")
            st.rerun()
        presets = [p.stem for p in list_ladder_presets()]
        if presets:
            choice = st.selectbox(
                "preset YAML",
                presets,
                index=presets.index("beam_evolution") if "beam_evolution" in presets else 0,
            )
            if st.button("LOAD PRESET", width="stretch"):
                st.session_state.ladder_doc = load_ladder_preset(choice)
                st.rerun()
    with p2:
        st.caption("SCAN")
        doc.scan_active = st.toggle("RUNG SCAN", value=doc.scan_active)
        doc.edit_mode = st.toggle("EDIT MODE", value=doc.edit_mode)
        c1, c2, c3 = st.columns(3)
        if c1.button("STEP"):
            engine.tick(doc)
        if c2.button("RESET"):
            doc.cycle = 0
            doc.frame_index = 0
        if c3.button("HALT"):
            doc.scan_active = False
        st.caption(f"frame {doc.frame_index + 1}/{doc.n_pulse_frames}")
        if doc.edit_mode:
            st.caption("RUNGS")
            r1, r2, r3, r4 = st.columns(4)
            if r1.button("ADD"):
                doc.add_rung()
            if r2.button("DEL") and doc.selected_node_id:
                doc.delete_rung(doc.selected_node_id.split(".", 1)[0])
            if r3.button("UP") and doc.selected_node_id:
                doc.move_rung(doc.selected_node_id.split(".", 1)[0], -1)
            if r4.button("DOWN") and doc.selected_node_id:
                doc.move_rung(doc.selected_node_id.split(".", 1)[0], 1)
    with p3:
        st.caption("TAG INSPECTOR")
        if doc.selected_node_id:
            st.code(doc.selected_node_id)
            rung = doc.node_rung(doc.selected_node_id)
            local = doc.selected_node_id.split(".", 1)[-1]
            if rung:
                for c in rung.contacts:
                    if c.id == local:
                        c.tag = st.text_input("tag", c.tag).upper()
                        kinds = ["NO", "NC", "trigger", "param"]
                        c.kind = st.selectbox(
                            "kind", kinds, index=kinds.index(c.kind) if c.kind in kinds else 0
                        )
                        c.closed = st.toggle("closed / energized", value=c.closed)
                        c.value = st.text_input("value", c.value)
                        c.help = st.text_input("help", c.help)
                        if st.button("TRIGGER NODE"):
                            doc.trigger(c.node_id(rung.id))
                            st.rerun()
                for d in rung.equipment:
                    if d.id == local:
                        d.tag = st.text_input("device tag", d.tag)
                        d.name = st.text_input("name", d.name)
                        d.help = st.text_input("help", d.help)
                kind = st.text_input("workbench kind", str(rung.workbench.get("kind", "identity")))
                rung.workbench["kind"] = kind
                params = dict(rung.workbench.get("params") or {})
                if kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
                    params["ell"] = int(st.number_input("ell", value=int(params.get("ell", 1))))
                rung.workbench["params"] = params
        else:
            st.caption("select a node")
    with p4:
        st.caption("FILE / WORKBENCH")
        dumped = io.StringIO()
        yaml.safe_dump(doc.as_dict(), dumped, sort_keys=False)
        st.download_button("SAVE YAML", dumped.getvalue(), file_name="ladder.yaml", mime="text/yaml")
        st.download_button(
            "EXPORT IL",
            export_instruction_list(doc),
            file_name="ladder.il.txt",
            mime="text/plain",
            help="Plain-text PLC instruction list (documentation).",
        )
        with st.expander("LOAD YAML"):
            up = st.file_uploader("file", type=["yaml", "yml"], label_visibility="collapsed")
            if up is not None:
                st.session_state.ladder_doc = LadderDocument.from_dict(yaml.safe_load(up.getvalue()))
                st.rerun()
        if st.button("simulate selected"):
            try:
                engine.call_workbench(doc, "simulate")
                st.caption("simulate_modes ok")
            except Exception as exc:
                st.caption(f"{type(exc).__name__}: {exc}")
        if st.button("export-slm"):
            try:
                path = engine.call_workbench(doc, "export-slm")
                st.caption(f"wrote {path}")
            except Exception as exc:
                st.caption(f"{type(exc).__name__}: {exc}")
        if st.button("run-vqc"):
            try:
                result = engine.call_workbench(doc, "run-vqc")
                st.json(result.summarize())
            except Exception as exc:
                st.caption(f"{type(exc).__name__}: {exc}")
        if st.button("hitl playlist"):
            try:
                result = engine.call_workbench(doc, "hitl")
                st.caption(result.summary() if hasattr(result, "summary") else "hitl ok")
            except Exception as exc:
                st.caption(f"{type(exc).__name__}: {exc}")


def _chip(st, label: str, node_id: str, doc: LadderDocument, help_txt: str = "") -> None:
    selected = doc.selected_node_id == node_id
    if st.button(
        label,
        key=node_id,
        type="primary" if selected else "secondary",
        help=help_txt or label,
    ):
        _select(st, doc, node_id)


def _app() -> None:
    import streamlit as st

    from vqc_workbench import __version__
    from vqc_workbench.ladder.engine import LadderEngine

    st.set_page_config(
        page_title="Photonic Ladder Diagram",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(LADDER_CSS, unsafe_allow_html=True)

    args = _parse_args()
    doc = _ensure_doc(st, args.yaml)
    doc.version = __version__
    engine = st.session_state.setdefault("ladder_engine", LadderEngine(grid_size=doc.grid_size))

    runtime = engine.bind(doc)

    scan = "ACTIVE" if doc.scan_active else "HALT"
    scan_cls = "on" if doc.scan_active else ""
    edit = "EDIT MODE" if doc.edit_mode else "RUN MODE"
    st.markdown(
        f"""<div class="ladder-title">
        <div>{doc.title} | VQC Workbench v{doc.version}</div>
        <div class="status">
          <span>RUNG SCAN: <span class="{scan_cls}">{scan}</span></span>
          <span>CYCLE: {int(doc.cycle):05d}</span>
          <span>{edit}</span>
        </div></div>""",
        unsafe_allow_html=True,
    )
    with st.expander("PROGRAM  —  presets / scan / tags / file / Workbench", expanded=True):
        _program_panel(st, doc, engine)

    spec = runtime.spectrum
    auto = str((spec.extras or {}).get("auto_axis") or "ell")
    st.markdown(
        '<div class="ladder-strip"><span class="help-chip">SPECTRUM ANALYZER  —  Selected Node Signal</span></div>',
        unsafe_allow_html=True,
    )
    sc1, sc2, sc3 = st.columns([3.2, 0.7, 1.05])
    with sc1:
        st.pyplot(_spectrum_fig(spec), width="stretch")
    with sc2:
        st.caption("AXIS")
        if st.button("AUTO", type="primary" if doc.spectrum_axis is None else "secondary"):
            doc.spectrum_axis = None
            st.rerun()
        if st.button("ell", type="primary" if doc.spectrum_axis == "ell" else "secondary"):
            doc.spectrum_axis = "ell"
            st.rerun()
        if st.button("wl nm", type="primary" if doc.spectrum_axis == "wavelength_nm" else "secondary"):
            doc.spectrum_axis = "wavelength_nm"
            st.rerun()
        st.caption(f"auto={auto}")
    with sc3:
        st.markdown(
            f"""<div class="readout">
            NODE  {spec.node_name}<br/>
            PEAK  {spec.peak_label}<br/>
            FWHM  {spec.fwhm:.2f}<br/>
            AXIS  {spec.axis}
            </div>""",
            unsafe_allow_html=True,
        )
        if spec.extras.get("expected_ell") is not None:
            st.caption(f"forecast ell={int(spec.extras['expected_ell']):+d}")
        if spec.extras.get("expectation_ell") is not None:
            st.caption(f"<ell> {float(spec.extras['expectation_ell']):+.2f}")

    if doc.alarm:
        st.markdown(f'<div class="help-chip">ALARM  {doc.alarm}</div>', unsafe_allow_html=True)

    for rung in doc.rungs:
        state = runtime.rungs[rung.id]
        ell_txt = f"  ell={state.dominant_ell:+d}" if state.dominant_ell is not None else ""
        st.markdown(
            f'<div class="rung-head">LOGIC RUNG {rung.number:02d}  {rung.title}  —  {rung.subtitle}'
            f"&nbsp;&nbsp; WB {state.kind}{ell_txt}</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="logic-wrap">', unsafe_allow_html=True)
        rail_l, tags, axp, stp, rail_r = st.columns([0.05, 0.40, 0.25, 0.25, 0.05], vertical_alignment="center")
        with rail_l:
            klass = "rail-bar selected" if doc.selected_node_id == f"{rung.id}.rail_l" else "rail-bar"
            st.markdown(f'<div class="{klass}"></div>', unsafe_allow_html=True)
            _chip(st, "L", f"{rung.id}.rail_l", doc, "left power rail")
        with tags:
            n = max(1, len(rung.contacts))
            cols = st.columns(n)
            for col, contact in zip(cols, rung.contacts):
                led = "◆" if contact.closed else "◇"
                with col:
                    _chip(st, f"{led} {contact.tag}", contact.node_id(rung.id), doc, contact.help or contact.tag)
        with axp:
            if rung.axial:
                nid = rung.axial.node_id(rung.id)
                st.markdown(_monitor_html(state.axial, rung.axial, doc.selected_node_id == nid), unsafe_allow_html=True)
                _chip(st, "AX", nid, doc, rung.axial.help or "axial / phase-front")
        with stp:
            if rung.spatiotemporal:
                nid = rung.spatiotemporal.node_id(rung.id)
                st.markdown(
                    _monitor_html(state.spatiotemporal, rung.spatiotemporal, doc.selected_node_id == nid),
                    unsafe_allow_html=True,
                )
                _chip(st, "ST", nid, doc, rung.spatiotemporal.help or "spatiotemporal / length")
        with rail_r:
            klass = "rail-bar selected" if doc.selected_node_id == f"{rung.id}.rail_r" else "rail-bar"
            st.markdown(f'<div class="{klass}"></div>', unsafe_allow_html=True)
            _chip(st, "R", f"{rung.id}.rail_r", doc, "right power rail")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="equip-head">EQUIPMENT / LAB MAPPING</div>', unsafe_allow_html=True)
        st.markdown('<div class="equip-wrap">', unsafe_allow_html=True)
        ecols = st.columns(max(1, len(rung.equipment)))
        for col, dev in zip(ecols, rung.equipment):
            with col:
                _chip(st, f"{dev.tag}  {dev.name}", dev.node_id(rung.id), doc, dev.help or dev.name)
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.ladder_doc = doc


if __name__ == "__main__":
    _app()
