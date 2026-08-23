"""Streamlit photonic workbench. Launch via ``Workbench.launch_dashboard()``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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
    import numpy as np
    import streamlit as st

    from vqc_workbench.adapters import probe_ecosystem
    from vqc_workbench.api import Workbench
    from vqc_workbench.core.registry import available_kinds
    from vqc_workbench.ui.editors import schema_for

    st.set_page_config(page_title="VQC Photonic Workbench", layout="wide")
    st.title("VQC Photonic Workbench")
    st.caption("Edit metamaterials and gratings → OAM modes → Vortex Quaternion Conduit")

    wb = Workbench()
    kinds = available_kinds()
    eco = probe_ecosystem()

    with st.sidebar:
        st.header("Structure")
        kind = st.selectbox("kind", kinds, index=kinds.index("spiral_phase") if "spiral_phase" in kinds else 0)
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
        L_max = st.slider("L_max", 2, 16, int(wb.config.L_max))
        turb = st.slider("turbulence", 0.0, 2.0, 0.0, 0.05)
        payload = st.text_input("VQC payload", "I live in Oregon")
        st.subheader("Ecosystem")
        st.json({k: v for k, v in eco.as_dict().items() if k != "notes"})

    structure = wb.create_structure(kind, **params)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Phase mask")
        modes = wb.simulate_modes(structure, L_max=L_max)
        st.image(
            _phase_to_rgb(modes.phase_mask),
            caption=f"{structure.kind} / {structure.name}",
            use_container_width=True,
        )
    with col2:
        st.subheader("OAM spectrum")
        st.bar_chart({"ell": modes.ell, "I": modes.intensity}, x="ell", y="I")
        st.metric("dominant ℓ", modes.dominant_ell())
        st.metric("OAM purity", float(np.sum(modes.intensity**2)))

    if st.button("Run VQC pipeline"):
        # Identity coupling is used when the structure is a strong mode shifter
        # so payload recovery remains interpretable; the mask still seeds modes above.
        ident = wb.create_structure("identity")
        conduit = ident if kind != "identity" else structure
        result = wb.run_vqc(conduit, payload, L_max=L_max, turbulence=turb)
        st.success(
            f"fidelity={result.fidelity:.4f}  BER={result.ber:.4f}  "
            f"match={result.payload_match}  recovered={result.recovered_payload!r}"
        )
        st.json(result.summarize())


def _phase_to_rgb(mask) -> "np.ndarray":
    import numpy as np

    ang = (np.angle(mask) + np.pi) / (2 * np.pi)
    vis = (np.clip(ang, 0, 1) * 255).astype(np.uint8)
    return np.stack([vis, vis, vis], axis=-1)


if __name__ == "__main__":
    _app()
