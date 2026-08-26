"""Photonic ladder HMI. Launch via ``Workbench.launch_ladder()`` or ``vqc-workbench ladder``."""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

from vqc_workbench.ladder.model import SELECT_GLOW, LadderDocument, beam_evolution_ladder, load_ladder

LADDER_CSS = f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap");
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: #1a1d21 !important;
  color: #c8ced6;
}}
[data-testid="stHeader"] {{ background: #1a1d21 !important; }}
[data-testid="stToolbar"] {{ display: none; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
  padding: 0.35rem 0.8rem 1.2rem 0.8rem;
  max-width: 100%;
}}
h1, h2, h3, p, label, span, div {{
  font-family: "Share Tech Mono", "DejaVu Sans Mono", "Consolas", monospace !important;
}}
.stButton > button {{
  background: #1c2026;
  color: #c8ced6;
  border: 1px solid #4c5360;
  border-radius: 0 !important;
  font-family: "Share Tech Mono", "DejaVu Sans Mono", monospace !important;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  padding: 0.18rem 0.45rem;
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
  box-shadow: 0 0 10px 2px {SELECT_GLOW} !important;
}}
[data-testid="stSidebar"] {{
  background: #16191d;
}}
hr {{ border-color: #4c5360 !important; }}
.ladder-title {{
  background: #1e2228;
  border: 1px solid #4c5360;
  padding: 0.45rem 0.7rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #d5dbe3;
  font-size: 0.95rem;
}}
.ladder-title .status span {{ margin-left: 1.1rem; color: #7d8693; }}
.ladder-title .on {{ color: #3dcc7a; }}
.ladder-strip {{
  background: #23272e;
  border: 1px solid #4c5360;
  border-top: none;
  padding: 0.25rem 0.7rem 0.45rem 0.7rem;
}}
.rung-head, .equip-head {{
  background: #1e2329;
  border: 1px solid #4c5360;
  color: #7d8693;
  font-size: 0.78rem;
  padding: 0.2rem 0.55rem;
  letter-spacing: 0.06em;
}}
.logic-wrap, .equip-wrap {{
  background: #23272e;
  border: 1px solid #4c5360;
  border-top: none;
  padding: 0.45rem 0.4rem 0.55rem 0.4rem;
  margin-bottom: 0;
}}
.equip-wrap {{
  background: #1f242b;
  margin-bottom: 0.65rem;
}}
.rail {{
  width: 4px;
  background: #c5ccd4;
  min-height: 92px;
}}
.mon-bezel {{
  background: #16191d;
  border: 1px solid #4c5360;
  padding: 0.2rem;
}}
.mon-bezel.selected {{
  border: 1px solid {SELECT_GLOW};
  box-shadow: 0 0 10px 2px {SELECT_GLOW};
}}
.mon-cap {{
  color: #7d8693;
  font-size: 0.68rem;
  display: flex;
  justify-content: space-between;
}}
.help-chip {{
  color: #7d8693;
  font-size: 0.72rem;
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


def _spectrum_fig(spec) -> "object":
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11.2, 1.85), facecolor="#23272e")
    ax.set_facecolor("#16191d")
    x, y = spec.x, spec.y
    if spec.axis == "ell":
        ax.bar(x, y, width=0.78, color="#3d8a6a", edgecolor="#1e3d32", linewidth=0.4)
        ax.set_xlabel("MODE  ell")
    else:
        ax.plot(x, y, color="#6ec4a8", lw=1.3)
        ax.fill_between(x, y, color="#3d8a6a", alpha=0.35)
        ax.set_xlabel("WAVELENGTH  nm")
    ax.set_ylabel("INTENSITY")
    ax.tick_params(colors="#7d8693", labelsize=8)
    ax.xaxis.label.set_color("#7d8693")
    ax.yaxis.label.set_color("#7d8693")
    for spine in ax.spines.values():
        spine.set_color("#4c5360")
    ax.grid(True, axis="y", color="#2e333c", lw=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def _app() -> None:
    import streamlit as st

    from vqc_workbench import __version__
    from vqc_workbench.ladder.engine import LadderEngine

    st.set_page_config(
        page_title="Photonic Ladder Diagram",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(LADDER_CSS, unsafe_allow_html=True)

    args = _parse_args()
    doc = _ensure_doc(st, args.yaml)
    doc.version = __version__
    engine = st.session_state.setdefault("ladder_engine", LadderEngine(grid_size=doc.grid_size))

    with st.sidebar:
        st.markdown("**PROGRAM**")
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
        st.divider()
        if doc.edit_mode:
            st.markdown("**RUNGS**")
            r1, r2, r3 = st.columns(3)
            if r1.button("ADD"):
                doc.add_rung()
            if r2.button("DEL") and doc.selected_node_id:
                rid = doc.selected_node_id.split(".", 1)[0]
                doc.delete_rung(rid)
            if r3.button("UP") and doc.selected_node_id:
                doc.move_rung(doc.selected_node_id.split(".", 1)[0], -1)
            if st.button("DOWN") and doc.selected_node_id:
                doc.move_rung(doc.selected_node_id.split(".", 1)[0], 1)
            st.divider()
            st.markdown("**TAG INSPECTOR**")
            if doc.selected_node_id:
                st.code(doc.selected_node_id)
                rung = doc.node_rung(doc.selected_node_id)
                local = doc.selected_node_id.split(".", 1)[-1]
                if rung:
                    for c in rung.contacts:
                        if c.id == local:
                            c.tag = st.text_input("tag", c.tag).upper()
                            c.kind = st.selectbox("kind", ["NO", "NC", "trigger", "param"], index=["NO", "NC", "trigger", "param"].index(c.kind) if c.kind in {"NO", "NC", "trigger", "param"} else 0)
                            c.closed = st.toggle("closed / energized", value=c.closed)
                            c.value = st.text_input("value", c.value)
                            c.help = st.text_input("help", c.help)
                            if st.button("TRIGGER NODE"):
                                doc.trigger(c.node_id(rung.id))
                    for d in rung.equipment:
                        if d.id == local:
                            d.tag = st.text_input("device tag", d.tag)
                            d.name = st.text_input("name", d.name)
                            d.help = st.text_input("help", d.help)
                    kind = st.text_input("workbench kind", str(rung.workbench.get("kind", "identity")))
                    rung.workbench["kind"] = kind
                    params = dict(rung.workbench.get("params") or {})
                    if kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
                        params["ell"] = int(
                            st.number_input("ell", value=int(params.get("ell", 1)))
                        )
                    rung.workbench["params"] = params
            st.divider()
        st.markdown("**FILE**")
        dumped = io.StringIO()
        import yaml

        yaml.safe_dump(doc.as_dict(), dumped, sort_keys=False)
        st.download_button("SAVE YAML", dumped.getvalue(), file_name="ladder.yaml", mime="text/yaml")
        up = st.file_uploader("LOAD YAML", type=["yaml", "yml"])
        if up is not None:
            import yaml as _yaml

            st.session_state.ladder_doc = LadderDocument.from_dict(_yaml.safe_load(up.getvalue()))
            st.rerun()
        st.divider()
        st.markdown("**WORKBENCH**")
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

    runtime = engine.bind(doc)
    if doc.scan_active:
        engine.tick(doc)

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

    spec = runtime.spectrum
    st.markdown(
        '<div class="ladder-strip"><span class="help-chip">SPECTRUM ANALYZER  —  Selected Node Signal</span></div>',
        unsafe_allow_html=True,
    )
    sc1, sc2 = st.columns([3.4, 1.0])
    with sc1:
        st.pyplot(_spectrum_fig(spec), width="stretch")
    with sc2:
        st.markdown(
            f"""<div class="mon-bezel">
            <div>NODE  {spec.node_name}</div>
            <div>PEAK  {spec.peak_label}</div>
            <div>FWHM  {spec.fwhm:.2f}</div>
            <div>AXIS  {spec.axis}</div>
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
        st.markdown(
            f'<div class="rung-head">LOGIC RUNG {rung.number:02d}  {rung.title}  —  {rung.subtitle}'
            f'&nbsp;&nbsp; WB {state.kind}'
            f'{"  ell=" + f"{state.dominant_ell:+d}" if state.dominant_ell is not None else ""}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="logic-wrap">', unsafe_allow_html=True)
        left, axp, stp = st.columns([3.15, 1.22, 1.22], vertical_alignment="center")
        with left:
            rail_l, tags, rail_r = st.columns([0.08, 3.0, 0.08])
            with rail_l:
                sel_l = doc.selected_node_id == f"{rung.id}.rail_l"
                if st.button("│", key=f"{rung.id}.rail_l", type="primary" if sel_l else "secondary"):
                    _select(st, doc, f"{rung.id}.rail_l")
            with tags:
                cols = st.columns(max(1, len(rung.contacts)))
                for col, contact in zip(cols, rung.contacts):
                    nid = contact.node_id(rung.id)
                    selected = doc.selected_node_id == nid
                    led = "◆" if contact.closed else "◇"
                    label = f"{led} {contact.tag}"
                    with col:
                        if st.button(
                            label,
                            key=nid,
                            type="primary" if selected else "secondary",
                            help=contact.help or contact.tag,
                        ):
                            _select(st, doc, nid)
                        st.caption("⚙ " + (contact.kind if not contact.value else f"{contact.kind}={contact.value}"))
            with rail_r:
                sel_r = doc.selected_node_id == f"{rung.id}.rail_r"
                if st.button("│", key=f"{rung.id}.rail_r", type="primary" if sel_r else "secondary"):
                    _select(st, doc, f"{rung.id}.rail_r")
        def _mon(col, rgb, monitor, nid):
            selected = doc.selected_node_id == nid
            klass = "mon-bezel selected" if selected else "mon-bezel"
            title = monitor.title if monitor else "MONITOR"
            flabel = monitor.frame_label() if monitor else ""
            scale = monitor.scale if monitor else ""
            with col:
                st.markdown(
                    f'<div class="{klass}"><div class="mon-cap"><span>{title}</span><span>{flabel}</span></div></div>',
                    unsafe_allow_html=True,
                )
                st.image(rgb, width="stretch")
                st.caption(scale)
                if st.button("SEL", key=nid, type="primary" if selected else "secondary", help=monitor.help if monitor else ""):
                    _select(st, doc, nid)

        if rung.axial:
            _mon(axp, state.axial, rung.axial, rung.axial.node_id(rung.id))
        if rung.spatiotemporal:
            _mon(stp, state.spatiotemporal, rung.spatiotemporal, rung.spatiotemporal.node_id(rung.id))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div class="equip-head">EQUIPMENT / LAB MAPPING</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="equip-wrap">', unsafe_allow_html=True)
        ecols = st.columns(max(1, len(rung.equipment)))
        for col, dev in zip(ecols, rung.equipment):
            nid = dev.node_id(rung.id)
            selected = doc.selected_node_id == nid
            with col:
                if st.button(
                    f"{dev.tag}\n{dev.name}",
                    key=nid,
                    type="primary" if selected else "secondary",
                    help=dev.help or dev.name,
                ):
                    _select(st, doc, nid)
                st.caption(f"⚙ {dev.kind}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.ladder_doc = doc


if __name__ == "__main__":
    _app()
