"""Streamlit photonic workbench. Launch via ``Workbench.launch_dashboard()``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DASHBOARD_KINDS_HIDDEN = {"cascade", "matched_filter", "custom"}


def dashboard_script() -> Path:
    return Path(__file__).resolve()


def launch_dashboard(port: int = 8501) -> None:
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
        str(dashboard_script()),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    raise SystemExit(subprocess.call(cmd))


def _app() -> None:
    import streamlit as st

    from vqc_workbench.adapters import probe_ecosystem
    from vqc_workbench.api import Workbench
    from vqc_workbench.core.registry import available_kinds
    from vqc_workbench.ui.editors import schema_for

    st.set_page_config(page_title="VQC Photonic Workbench", layout="wide")
    st.title("VQC Photonic Workbench")
    st.caption("Edit metamaterials and gratings → OAM modes → Vortex Quaternion Conduit")

    wb = Workbench()
    kinds = [k for k in available_kinds() if k not in DASHBOARD_KINDS_HIDDEN]
    eco = probe_ecosystem()
    eco_dict = eco.as_dict()
    notes = eco_dict.pop("notes", {}) if isinstance(eco_dict, dict) else {}

    with st.sidebar:
        st.header("Structure")
        default_idx = kinds.index("spiral_phase") if "spiral_phase" in kinds else 0
        kind = st.selectbox("kind", kinds, index=default_idx)
        params: dict = {}
        for field in schema_for(kind):
            if field["type"] == "int":
                params[field["name"]] = st.slider(
                    field["name"], int(field["min"]), int(field["max"]), int(field["default"])
                )
            else:
                params[field["name"]] = st.slider(
                    field["name"], float(field["min"]), float(field["max"]), float(field["default"])
                )
        if kind == "trajectoid":
            params["live"] = st.toggle(
                "live generate_shell",
                value=False,
                help="Replace analytic cosine trenches with flux_trajectoid.generate_shell. "
                "Jacobi–Anger ℓ = w − n applies only to the analytic cell.",
                disabled=not eco.flux_trajectoid,
            )
        L_max = st.slider("L_max", 2, 16, int(wb.config.L_max))
        live_turb = st.toggle("Live turbulence on spectrum", value=False)
        turb = st.slider("turbulence", 0.0, 2.0, 0.0, 0.05, help="Used by VQC runs always; also by the spectrum when live turbulence is on.")
        payload = st.text_input("VQC payload", "Hi")
        st.divider()
        st.subheader("Neighboring packages")
        discovered = [k for k, v in eco_dict.items() if v]
        missing = [k for k, v in eco_dict.items() if not v]
        st.metric("discovered", len(discovered))
        st.success(", ".join(discovered) if discovered else "none")
        if missing:
            st.caption("not installed: " + ", ".join(missing))
        if notes:
            with st.expander("notes"):
                st.json(notes)

    structure = wb.create_structure(kind, **params)
    forecast = wb.forecast_charge(structure)
    spec_turb = turb if live_turb else 0.0
    modes = wb.simulate_modes(structure, L_max=L_max, turbulence=spec_turb)
    purity = float((modes.intensity**2).sum())

    with st.sidebar:
        if live_turb:
            st.metric("live purity", f"{purity:.3f}", delta=f"{purity - 1.0:.3f}")
            trace = st.session_state.setdefault("purity_trace", [])
            trace.append(purity)
            st.session_state.purity_trace = trace[-48:]
            st.line_chart(st.session_state.purity_trace, height=90)
            st.caption("Purity sparkline (last ~48 reruns). Drag turbulence to watch it fall.")
        else:
            st.session_state.purity_trace = []

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Phase mask")
        st.image(
            _phase_to_rgb(modes.phase_mask),
            caption=f"{structure.kind} / {structure.name}",
            width="stretch",
        )
    with col2:
        st.subheader("OAM spectrum")
        st.bar_chart({"ell": modes.ell, "I": modes.intensity}, x="ell", y="I")
        expected_label = "—" if forecast.expected_ell is None else str(forecast.expected_ell)
        m0, m1, m2, m3 = st.columns(4)
        m0.metric("expected ℓ", expected_label)
        m1.metric("dominant ℓ", modes.dominant_ell())
        m2.metric("⟨ℓ⟩", f"{modes.expectation_ell():.2f}")
        m3.metric("OAM purity", f"{purity:.3f}")
        st.caption(forecast.formula)
        if forecast.notes:
            st.caption(forecast.notes)
        if (
            forecast.expected_ell is not None
            and spec_turb == 0.0
            and modes.dominant_ell() == forecast.expected_ell
        ):
            st.success("Measured peak matches the topological arithmetic.")
        if live_turb and turb > 0:
            st.caption("Live Kolmogorov screen active — purity is no longer expected to be 1.0")

    st.subheader("Run VQC")
    if forecast.mode_shifter:
        st.info(
            f"This optic is a **mode shifter** (expected ℓ = {expected_label}). "
            "Payload recovery belongs on the identity channel or after the matched filter."
        )
    else:
        st.caption(
            "Identity is the recovery channel. Compensate applies a matched filter "
            "when the optic adds topological charge."
        )

    if forecast.mode_shifter:
        b1, b2, b3 = st.columns([1.0, 1.0, 1.35])
    else:
        b1, b2, b3 = st.columns(3)
    run_ident = b1.button("Identity channel", width="stretch")
    run_struct = b2.button(f"Through {kind}", width="stretch")
    run_matched = b3.button(
        "Compensate (matched filter)",
        width="stretch",
        type="primary" if forecast.mode_shifter else "secondary",
    )

    ident = wb.create_structure("identity")
    results = []
    if run_ident:
        results.append(("identity", wb.run_vqc(ident, payload, L_max=L_max, turbulence=turb)))
    if run_struct:
        results.append((kind, wb.run_vqc(structure, payload, L_max=L_max, turbulence=turb)))
    if run_matched:
        results.append(
            (
                f"{kind} + matched",
                wb.run_vqc(structure, payload, L_max=L_max, turbulence=turb, compensate=True),
            )
        )

    if results:
        cols = st.columns(len(results))
        for col, (label, result) in zip(cols, results):
            with col:
                st.markdown(f"**{label}**")
                st.metric("fidelity", f"{result.fidelity:.4f}")
                st.metric("BER", f"{result.ber:.4f}")
                st.metric("match", str(result.payload_match))
                recovered = result.recovered_payload
                try:
                    text = recovered.decode("utf-8")
                except UnicodeDecodeError:
                    text = recovered.hex()
                st.code(text)
                st.json(result.summarize())


def _phase_to_rgb(mask) -> "np.ndarray":
    import numpy as np

    ang = (np.angle(mask) + np.pi) / (2 * np.pi)
    vis = (np.clip(ang, 0, 1) * 255).astype(np.uint8)
    return np.stack([vis, vis, vis], axis=-1)


if __name__ == "__main__":
    _app()
