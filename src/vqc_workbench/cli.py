"""Command-line entry: ``vqc-workbench``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vqc-workbench", description="VQC photonic workbench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sim = sub.add_parser("simulate", help="structure → OAM mode spectrum")
    p_sim.add_argument("--kind", default="spiral_phase")
    p_sim.add_argument("--ell", type=int, default=3)
    p_sim.add_argument("--L-max", dest="L_max", type=int, default=None)
    p_sim.add_argument("--yaml", type=Path, default=None)

    p_vqc = sub.add_parser("run-vqc", help="end-to-end VQC pipeline")
    p_vqc.add_argument("--kind", default="identity")
    p_vqc.add_argument("--payload", default="I live in Oregon")
    p_vqc.add_argument("--turbulence", type=float, default=0.0)
    p_vqc.add_argument("--L-max", dest="L_max", type=int, default=None)

    p_slm = sub.add_parser("export-slm", help="write SLM phase + levels")
    p_slm.add_argument("--kind", default="spiral_phase")
    p_slm.add_argument("--ell", type=int, default=3)
    p_slm.add_argument("--out", type=Path, default=Path("outputs/slm_phase.npy"))
    p_slm.add_argument("--device", default="generic_512")

    p_ui = sub.add_parser("dashboard", help="launch Streamlit UI")
    p_ui.add_argument("--port", type=int, default=8501)

    sub.add_parser("status", help="ecosystem probe")

    args = parser.parse_args(argv)

    from vqc_workbench.api import Workbench

    wb = Workbench()

    if args.cmd == "status":
        print(json.dumps(wb.ecosystem.as_dict(), indent=2))
        return 0

    if args.cmd == "dashboard":
        wb.launch_dashboard(port=args.port)
        return 0

    if args.cmd == "simulate":
        if args.yaml:
            structure = wb.load_structure(args.yaml)
        else:
            kwargs = {}
            if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
                kwargs["ell"] = args.ell
            structure = wb.create_structure(args.kind, **kwargs)
        modes = wb.simulate_modes(structure, L_max=args.L_max)
        print(f"kind={structure.kind} dominant_ell={modes.dominant_ell()}")
        for e, c, i in zip(modes.ell, modes.coefficients, modes.intensity):
            if i > 1e-3:
                print(f"  ell={int(e):+d}  |c|={abs(c):.4g}  I={i:.4f}")
        return 0

    if args.cmd == "run-vqc":
        structure = wb.create_structure(args.kind)
        result = wb.run_vqc(
            structure,
            args.payload,
            L_max=args.L_max,
            turbulence=args.turbulence,
        )
        print(json.dumps(result.summarize(), indent=2, default=str))
        return 0 if result.payload_match else 1

    if args.cmd == "export-slm":
        kwargs = {}
        if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
            kwargs["ell"] = args.ell
        structure = wb.create_structure(args.kind, **kwargs)
        path = wb.export_slm(structure, args.out, device=args.device)
        print(f"wrote {path}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
