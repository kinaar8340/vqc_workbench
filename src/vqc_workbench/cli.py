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
    p_sim.add_argument("--n-trenches", type=int, default=8)
    p_sim.add_argument("--winding", type=int, default=2)
    p_sim.add_argument(
        "--live",
        action="store_true",
        help="trajectoid: use flux_trajectoid.generate_shell instead of analytic trenches",
    )
    p_sim.add_argument("--payload-hash", default=None, help="trajectoid payload identity")
    p_sim.add_argument("--L-max", dest="L_max", type=int, default=None)
    p_sim.add_argument("--yaml", type=Path, default=None)
    p_sim.add_argument("--turbulence", type=float, default=0.0)

    p_vqc = sub.add_parser("run-vqc", help="end-to-end VQC pipeline")
    p_vqc.add_argument("--kind", default="identity")
    p_vqc.add_argument("--payload", default="I live in Oregon")
    p_vqc.add_argument("--turbulence", type=float, default=0.0)
    p_vqc.add_argument("--L-max", dest="L_max", type=int, default=None)
    p_vqc.add_argument(
        "--compensate",
        action="store_true",
        help="apply a matched filter after the structure (inverse shifter)",
    )
    p_vqc.add_argument("--ell", type=int, default=3)
    p_vqc.add_argument(
        "--live",
        action="store_true",
        help="trajectoid: use flux_trajectoid.generate_shell instead of analytic trenches",
    )
    p_vqc.add_argument("--n-trenches", type=int, default=8)
    p_vqc.add_argument("--winding", type=int, default=2)

    p_slm = sub.add_parser("export-slm", help="write SLM phase + levels")
    p_slm.add_argument("--kind", default="spiral_phase")
    p_slm.add_argument("--ell", type=int, default=3)
    p_slm.add_argument("--out", type=Path, default=Path("outputs/slm_phase.npy"))
    p_slm.add_argument("--device", default="generic_512")

    p_ui = sub.add_parser("dashboard", help="launch Streamlit UI")
    p_ui.add_argument("--port", type=int, default=8501)

    p_lad = sub.add_parser("ladder", help="photonic ladder diagram HMI")
    p_lad.add_argument("--port", type=int, default=8502)
    p_lad.add_argument("--yaml", type=Path, default=None, help="ladder program YAML")
    p_lad.add_argument("--preset", default=None, help="configs/ladders/<name>.yaml")
    p_lad.add_argument("--render", type=Path, default=None, help="write static HMI PNG and exit")
    p_lad.add_argument("--json", action="store_true", help="print bound ladder summary")
    p_lad.add_argument("--il", action="store_true", help="print PLC instruction list and exit")

    p_cmp = sub.add_parser("compare", help="modal vs full-wave OAM spectra")
    p_cmp.add_argument("--kind", default="binary_grating")
    p_cmp.add_argument("--ell", type=int, default=3)
    p_cmp.add_argument("--n-trenches", type=int, default=8)
    p_cmp.add_argument("--winding", type=int, default=2)
    p_cmp.add_argument("--backends", default="modal,scalar")
    p_cmp.add_argument("--L-max", dest="L_max", type=int, default=8)
    p_cmp.add_argument("--figure", type=Path, default=None, help="optional PNG path")
    p_cmp.add_argument(
        "--live",
        action="store_true",
        help="trajectoid: use flux_trajectoid.generate_shell instead of analytic trenches",
    )

    p_c = sub.add_parser("couple", help="couple OAM into an oam_flux Hopf lattice")
    p_c.add_argument("--kind", default="spiral_phase")
    p_c.add_argument("--ell", type=int, default=None)
    p_c.add_argument("--n-trenches", type=int, default=8)
    p_c.add_argument("--winding", type=int, default=2)
    p_c.add_argument("--kappa", type=float, default=0.85)
    p_c.add_argument("--steps", type=int, default=8)
    p_c.add_argument("--nx", type=int, default=12)
    p_c.add_argument("--kick", type=float, default=0.08)
    p_c.add_argument("--sweep-kappa", default=None, help="comma-separated κ list")
    p_c.add_argument("--L-max", dest="L_max", type=int, default=8)
    p_c.add_argument(
        "--json",
        action="store_true",
        help="print full result JSON including per-step history",
    )

    p_hitl = sub.add_parser("hitl", help="SLM playlist → vqc_demo projector proxy")
    p_hitl.add_argument("--payload", default="I live in Oregon")
    p_hitl.add_argument("--kind", default=None, help="optional structure for the phase playlist")
    p_hitl.add_argument("--ell", type=int, default=3)
    p_hitl.add_argument("--n-trenches", type=int, default=8)
    p_hitl.add_argument("--winding", type=int, default=2)
    p_hitl.add_argument("--device", default="generic_512")
    p_hitl.add_argument(
        "--channel",
        default="projector",
        help="clean | projector | harsh | kolmogorov | bmgl",
    )
    p_hitl.add_argument("--frames", type=int, default=8)
    p_hitl.add_argument("--out", type=Path, default=None, help="write playlist under this directory")
    p_hitl.add_argument(
        "--full",
        action="store_true",
        help="use 1920×1080 VPL-HW20A profile (default is the fast 320×180 loopback)",
    )
    p_hitl.add_argument("--capture", type=Path, default=None, help="decode an existing MP4 or PNG dir")
    p_hitl.add_argument(
        "--stitch",
        action="store_true",
        help="if --out is set, stitch proxy frames to MP4 (needs ffmpeg)",
    )
    p_hitl.add_argument("--json", action="store_true", help="print full result JSON")

    p_inv = sub.add_parser("inverse", help="inverse-design structure parameters")
    p_inv.add_argument("--kind", default="trajectoid")
    p_inv.add_argument("--objective", choices=["charge", "forecast", "fidelity"], default="charge")
    p_inv.add_argument("--target-ell", type=int, default=-6)
    p_inv.add_argument("--payload", default="Hi")
    p_inv.add_argument("--compensate", action="store_true")
    p_inv.add_argument("--L-max", dest="L_max", type=int, default=8)
    p_inv.add_argument("--max-evals", type=int, default=256)

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

    if args.cmd == "ladder":
        from vqc_workbench.ladder import (
            LadderEngine,
            beam_evolution_ladder,
            export_instruction_list,
            load_ladder,
            load_ladder_preset,
        )

        if args.preset:
            doc = load_ladder_preset(args.preset)
        elif args.yaml:
            doc = load_ladder(args.yaml)
        else:
            doc = beam_evolution_ladder()
        if args.il:
            print(export_instruction_list(doc), end="")
            return 0
        if args.render or args.json:
            import matplotlib

            matplotlib.use("Agg")
            engine = LadderEngine(workbench=wb, grid_size=int(doc.grid_size))
            runtime = engine.bind(doc)
            if args.json:
                summary = {
                    "title": doc.title,
                    "version": doc.version,
                    "selected_node_id": doc.selected_node_id,
                    "n_rungs": len(doc.rungs),
                    "rungs": [
                        {
                            "id": r.id,
                            "title": r.title,
                            "kind": runtime.rungs[r.id].kind,
                            "dominant_ell": runtime.rungs[r.id].dominant_ell,
                            "equipment": [d.tag for d in r.equipment],
                        }
                        for r in doc.rungs
                    ],
                    "spectrum": None if runtime.spectrum is None else runtime.spectrum.as_dict(),
                    "alarm": doc.alarm,
                }
                print(json.dumps(summary, indent=2, default=str))
            if args.render:
                from vqc_workbench.ladder.render import render_ladder

                render_ladder(doc, runtime, args.render)
                print(f"wrote {args.render}")
            return 0
        wb.launch_ladder(port=args.port, yaml_path=args.yaml)
        return 0

    if args.cmd == "simulate":
        if args.yaml:
            structure = wb.load_structure(args.yaml)
        else:
            kwargs = {}
            if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
                kwargs["ell"] = args.ell
            if args.kind == "trajectoid":
                kwargs["n_trenches"] = args.n_trenches
                kwargs["winding"] = args.winding
                kwargs["live"] = bool(args.live)
                if args.payload_hash:
                    kwargs["payload_hash"] = args.payload_hash
            structure = wb.create_structure(args.kind, **kwargs)
        forecast = wb.forecast_charge(structure)
        modes = wb.simulate_modes(structure, L_max=args.L_max, turbulence=args.turbulence)
        exp = "n/a" if forecast.expected_ell is None else f"{forecast.expected_ell:+d}"
        print(
            f"kind={structure.kind} expected_ell={exp}  "
            f"dominant_ell={modes.dominant_ell():+d}  ⟨ℓ⟩={modes.expectation_ell():.2f}"
        )
        if forecast.formula:
            print(f"  {forecast.formula}")
        for e, c, i in zip(modes.ell, modes.coefficients, modes.intensity):
            if i > 1e-3:
                print(f"  ell={int(e):+d}  |c|={abs(c):.4g}  I={i:.4f}")
        return 0

    if args.cmd == "run-vqc":
        kwargs = {}
        if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
            kwargs["ell"] = args.ell
        if args.kind == "trajectoid":
            kwargs["n_trenches"] = args.n_trenches
            kwargs["winding"] = args.winding
            kwargs["live"] = bool(args.live)
            kwargs["payload_hash"] = args.payload
        structure = wb.create_structure(args.kind, **kwargs)
        result = wb.run_vqc(
            structure,
            args.payload,
            L_max=args.L_max,
            turbulence=args.turbulence,
            compensate=args.compensate,
        )
        print(json.dumps(result.summarize(), indent=2, default=str))
        return 0 if result.payload_match else 1

    if args.cmd == "compare":
        kwargs = {}
        if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
            kwargs["ell"] = args.ell
        if args.kind == "trajectoid":
            kwargs["n_trenches"] = args.n_trenches
            kwargs["winding"] = args.winding
            kwargs["live"] = bool(getattr(args, "live", False))
        structure = wb.create_structure(args.kind, **kwargs)
        names = tuple(p.strip() for p in args.backends.split(",") if p.strip())
        if len(names) < 2:
            raise SystemExit("--backends needs at least two names, e.g. modal,scalar or modal,scalar,meep")
        cmp = wb.compare_backends(structure, backends=names, L_max=args.L_max)
        if "pairwise" in cmp:
            printable = {k: v for k, v in cmp.items() if k != "results"}
        else:
            printable = {k: v for k, v in cmp.items() if k not in {"ell", "intensity_a", "intensity_b"}}
        print(json.dumps(printable, indent=2, default=str))
        if args.figure:
            from vqc_workbench.ui.visualizers import plot_backend_spectra

            if "results" in cmp:
                series = cmp["results"]
            else:
                series = [
                    wb.simulate_fullwave(structure, backend=names[0], L_max=args.L_max),
                    wb.simulate_fullwave(structure, backend=names[1], L_max=args.L_max),
                ]
            fc = wb.forecast_charge(structure)
            plot_backend_spectra(
                series,
                expected_ell=fc.expected_ell,
                path=str(args.figure),
                title=f"{structure.kind}  expected ℓ = {fc.expected_ell}",
            )
            print(f"wrote {args.figure}")
        return 0

    if args.cmd == "couple":
        kwargs: dict = {}
        if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"} and args.ell is not None:
            kwargs["ell"] = args.ell
        if args.kind == "trajectoid":
            kwargs["n_trenches"] = args.n_trenches
            kwargs["winding"] = args.winding
        structure = wb.create_structure(args.kind, **kwargs)
        sweep = None
        if args.sweep_kappa:
            sweep = [float(x) for x in args.sweep_kappa.split(",") if x.strip()]
        result = wb.couple_to_lattice(
            structure,
            kappa=args.kappa,
            steps=args.steps,
            ell=args.ell,
            nx=args.nx,
            kick_strength=args.kick,
            sweep_kappa=sweep,
            L_max=args.L_max,
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, default=str))
        else:
            print(result.summary())
        return 0

    if args.cmd == "hitl":
        structure = None
        if args.kind:
            kwargs: dict = {}
            if args.kind in {"spiral_phase", "forked_hologram", "flux_lattice"}:
                kwargs["ell"] = args.ell
            if args.kind == "trajectoid":
                kwargs["n_trenches"] = args.n_trenches
                kwargs["winding"] = args.winding
            structure = wb.create_structure(args.kind, **kwargs)
        result = wb.hitl(
            args.payload,
            structure,
            device=args.device,
            channel=args.channel,
            n_frames=args.frames,
            out=args.out,
            full=args.full,
            capture=args.capture,
            stitch=args.stitch,
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, default=str))
        else:
            print(result.summary())
        return 0 if result.payload_match and result.crc_ok else 2

    if args.cmd == "inverse":
        result = wb.inverse_design(
            args.kind,
            objective=args.objective,
            target_ell=None if args.objective == "fidelity" else args.target_ell,
            payload=args.payload,
            compensate=args.compensate,
            L_max=args.L_max,
            max_evals=args.max_evals,
        )
        print(json.dumps(result.as_dict(), indent=2, default=str))
        return 0

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
