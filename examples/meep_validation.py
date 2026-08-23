#!/usr/bin/env python3
"""Meep validation suite: resolution sweep, spiral plate, dielectric slab.

    conda activate vqc-meep
    VQC_MEEP_RUN=1 PYTHONPATH=src python examples/meep_validation.py all

Subcommands: sweep | spiral | slab | all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vqc_workbench import Workbench
from vqc_workbench.core.config import workbench_root
from vqc_workbench.simulation.compare import compare_spectra
from vqc_workbench.simulation.fullwave import FullWaveUnavailable
from vqc_workbench.ui.visualizers import plot_backend_spectra


def _jsonable(value):
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _purity(result) -> float:
    return float((result.intensity**2).sum())


def _summary(result) -> dict:
    return {
        "backend": result.backend,
        "dominant_ell": int(result.dominant_ell()),
        "expectation_ell": float(result.expectation_ell()),
        "purity": _purity(result),
        "extras": _jsonable(result.extras),
    }


def _fig_dir() -> Path:
    d = workbench_root() / "docs" / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {path}")


def _triple(wb, structure, *, expected, fig_name, title, meep_kw):
    notes = {}
    results = []
    base = dict(L_max=meep_kw.pop("L_max", 8), grid_size=meep_kw.pop("grid_size", 40), w0=1.0)
    extent = meep_kw.pop("extent", 4.5)
    base["extent"] = extent
    for name, extra in (
        ("modal", {}),
        ("scalar", {"z": 0.0}),
        ("meep", meep_kw),
    ):
        try:
            results.append(wb.simulate_fullwave(structure, backend=name, **base, **extra))
            print(f"  {name}: ℓ={results[-1].dominant_ell():+d}  P={_purity(results[-1]):.3f}")
        except FullWaveUnavailable as exc:
            notes[name] = str(exc)
            print(f"  {name}: UNAVAILABLE — {exc}")
    if len(results) < 2:
        return {"unavailable": notes, "backends": [_summary(r) for r in results]}
    fig_path = _fig_dir() / fig_name
    plot_backend_spectra(results, expected_ell=expected, path=str(fig_path), title=title)
    print(f"wrote {fig_path}")
    pairwise = []
    meep_vs_modal = None
    for i, a in enumerate(results):
        for b in results[i + 1 :]:
            c = compare_spectra(a, b)
            row = {
                "a": a.backend,
                "b": b.backend,
                "cosine": c["cosine"],
                "dominant_match": c["dominant_match"],
                "dominant_ell_a": c["dominant_ell_a"],
                "dominant_ell_b": c["dominant_ell_b"],
            }
            pairwise.append(row)
            if {a.backend, b.backend} == {"modal", "meep"}:
                meep_vs_modal = row
    return {
        "expected_ell": expected,
        "backends": [_summary(r) for r in results],
        "pairwise": pairwise,
        "meep_vs_modal": meep_vs_modal,
        "unavailable": notes,
        "figure": str(fig_path),
    }


def cmd_sweep(wb: Workbench, resolutions: list[int]) -> dict:
    shell = wb.create_trajectoid(n_trenches=8, winding=2)
    expected = wb.forecast_charge(shell).expected_ell
    modal = wb.simulate_fullwave(shell, backend="modal", L_max=8, grid_size=40, extent=4.5)
    scalar = wb.simulate_fullwave(shell, backend="scalar", L_max=8, grid_size=40, extent=4.5, z=0.0)
    rows = []
    meep_results = []
    for res in resolutions:
        print(f"\n=== trajectoid source-imprint res={res} ===")
        try:
            meep = wb.simulate_fullwave(
                shell,
                backend="meep",
                L_max=8,
                grid_size=40,
                extent=4.5,
                resolution=res,
                layout="source_imprint",
            )
        except FullWaveUnavailable as exc:
            rows.append({"resolution": res, "error": str(exc)})
            print(f"  FAILED {exc}")
            continue
        meep_results.append(meep)
        vs = compare_spectra(modal, meep)
        row = {
            "resolution": res,
            "layout": "source_imprint",
            "dominant_ell": int(meep.dominant_ell()),
            "expectation_ell": float(meep.expectation_ell()),
            "purity": _purity(meep),
            "cosine_vs_modal": vs["cosine"],
            "dominant_match": vs["dominant_match"],
            "extras": _jsonable(meep.extras),
        }
        rows.append(row)
        print(
            f"  ℓ={row['dominant_ell']:+d}  P={row['purity']:.3f}  "
            f"cosine={row['cosine_vs_modal']:.3f}  match={row['dominant_match']}"
        )

    # Purity vs resolution plot (modal/scalar as dashed references).
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 3.6), constrained_layout=True)
    xs = [r["resolution"] for r in rows if "purity" in r]
    ys = [r["purity"] for r in rows if "purity" in r]
    cs = [r["cosine_vs_modal"] for r in rows if "purity" in r]
    ax.plot(xs, ys, "o-", color="#54A24B", label="Meep purity")
    ax.plot(xs, cs, "s--", color="#4C78A8", label="cosine vs modal")
    ax.axhline(_purity(modal), color="#4C78A8", ls=":", alpha=0.5, label="modal purity")
    ax.axhline(_purity(scalar), color="#F58518", ls=":", alpha=0.5, label="scalar purity")
    ax.set_xlabel("Meep resolution (pixels / unit length)")
    ax.set_ylabel("purity / cosine")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("trajectoid n=8, w=2  —  source-imprint resolution sweep")
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    sweep_fig = _fig_dir() / "trajectoid_meep_resolution_sweep.png"
    fig.savefig(sweep_fig, dpi=160)
    print(f"wrote {sweep_fig}")

    payload = {
        "expected_ell": expected,
        "formula": wb.forecast_charge(shell).formula,
        "modal": _summary(modal),
        "scalar": _summary(scalar),
        "sweep": rows,
        "figure": str(sweep_fig),
    }
    _write_json(_fig_dir() / "trajectoid_meep_resolution_sweep.json", payload)
    return payload


def cmd_spiral(wb: Workbench) -> dict:
    print("\n=== spiral_phase ell=+1 ===")
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    expected = wb.forecast_charge(plate).expected_ell
    payload = _triple(
        wb,
        plate,
        expected=expected,
        fig_name="spiral_backend_spectra.png",
        title=f"spiral phase plate  ell = +1  →  expected ℓ = {expected:+d}",
        meep_kw=dict(L_max=4, grid_size=32, extent=3.5, resolution=12, layout="source_imprint"),
    )
    payload["formula"] = wb.forecast_charge(plate).formula
    _write_json(_fig_dir() / "spiral_backend_spectra.json", payload)
    return payload


def cmd_slab(wb: Workbench) -> dict:
    print("\n=== thin_plate_3d  (larger cell, thicker PML) ===")
    out = {}
    # Cheaper sanity cell first.
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    out["spiral"] = _triple(
        wb,
        plate,
        expected=1,
        fig_name="spiral_thin_plate_spectra.png",
        title="spiral ell=+1  —  dielectric slab (thin_plate_3d)",
        meep_kw=dict(
            L_max=4,
            grid_size=32,
            extent=5.0,
            resolution=12,
            layout="thin_plate_3d",
            pml=1.2,
            sz=8.0,
            until=40,
            slab_thickness=0.5,
        ),
    )
    shell = wb.create_trajectoid(n_trenches=8, winding=2)
    out["trajectoid"] = _triple(
        wb,
        shell,
        expected=-6,
        fig_name="trajectoid_thin_plate_spectra.png",
        title="trajectoid n=8, w=2  —  dielectric slab (thin_plate_3d)",
        meep_kw=dict(
            L_max=8,
            grid_size=40,
            extent=6.0,
            resolution=16,
            layout="thin_plate_3d",
            pml=1.2,
            sz=8.0,
            until=40,
            slab_thickness=0.5,
        ),
    )
    _write_json(_fig_dir() / "thin_plate_3d.json", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Meep validation suite")
    parser.add_argument("cmd", nargs="?", default="all", choices=["sweep", "spiral", "slab", "all"])
    parser.add_argument("--resolutions", default="20,24,32", help="comma-separated Meep resolutions")
    args = parser.parse_args()
    resolutions = [int(x) for x in args.resolutions.split(",") if x.strip()]
    wb = Workbench()
    if args.cmd in {"sweep", "all"}:
        cmd_sweep(wb, resolutions)
    if args.cmd in {"spiral", "all"}:
        cmd_spiral(wb)
    if args.cmd in {"slab", "all"}:
        cmd_slab(wb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
