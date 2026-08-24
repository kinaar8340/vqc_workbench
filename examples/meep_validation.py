#!/usr/bin/env python3
"""Meep validation suite: resolution sweep, spiral plate, dielectric slab.

    conda activate vqc-meep
    VQC_MEEP_RUN=1 PYTHONPATH=src python examples/meep_validation.py all

Subcommands: sweep | spiral | slab | cells | slab-hires | all

    cells      — source-imprint binary / blazed / forked / metasurface
    slab-hires — thin_plate_3d spiral at higher res (default --resolutions 20,24,32)
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


def _cheap_imprint() -> dict:
    return dict(L_max=4, grid_size=32, extent=3.5, resolution=12, layout="source_imprint")


def cmd_cells(wb: Workbench) -> dict:
    """Source-imprint gallery past the canonical trajectoid / spiral cells."""
    print("\n=== source-imprint cells: binary, blazed, forked, metasurface ===")
    imprint = _cheap_imprint()
    specs = [
        (
            "binary_grating",
            wb.create_grating(kind="binary_grating", period=0.4, duty=0.5),
            "binary grating  period=0.4  —  source-imprint",
            dict(imprint),
        ),
        (
            "blazed_grating",
            wb.create_grating(kind="blazed_grating", period=0.5),
            "blazed grating  period=0.5  —  source-imprint",
            dict(imprint),
        ),
        (
            "forked_hologram",
            wb.create_grating(kind="forked_hologram", ell=1, period=0.35),
            "forked hologram  ell=+1  —  source-imprint",
            dict(imprint),
        ),
        (
            "metasurface",
            wb.create_metasurface(ell_target=1),
            "metasurface  ell_target=+1  —  source-imprint",
            dict(imprint),
        ),
    ]
    out: dict = {}
    for name, structure, title, meep_kw in specs:
        print(f"\n=== {name} ===")
        expected = wb.forecast_charge(structure).expected_ell
        payload = _triple(
            wb,
            structure,
            expected=expected,
            fig_name=f"{name}_backend_spectra.png",
            title=title,
            meep_kw=meep_kw,
        )
        payload["kind"] = name
        payload["formula"] = wb.forecast_charge(structure).formula
        payload["params"] = dict(structure.params)
        out[name] = payload
    _write_json(_fig_dir() / "meep_cells.json", out)
    return out


def cmd_slab_hires(wb: Workbench, resolutions: list[int]) -> dict:
    """Dielectric-slab spiral at higher res than the documented negative."""
    print("\n=== thin_plate_3d higher-res spiral (extent=3.5, sz=6) ===")
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    modal = wb.simulate_fullwave(plate, backend="modal", L_max=4, grid_size=32, extent=3.5)
    rows = []
    for res in resolutions:
        print(f"\n=== spiral thin_plate_3d res={res} ===")
        try:
            meep = wb.simulate_fullwave(
                plate,
                backend="meep",
                L_max=4,
                grid_size=32,
                extent=3.5,
                resolution=res,
                layout="thin_plate_3d",
                pml=1.0,
                sz=6.0,
                until=40,
                slab_thickness=0.5,
            )
        except FullWaveUnavailable as exc:
            rows.append({"resolution": res, "error": str(exc)})
            print(f"  FAILED {exc}")
            continue
        vs = compare_spectra(modal, meep)
        row = {
            "resolution": res,
            "layout": "thin_plate_3d",
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
        fig_path = _fig_dir() / f"spiral_thin_plate_res{res}.png"
        plot_backend_spectra(
            [modal, meep],
            expected_ell=1,
            path=str(fig_path),
            title=f"spiral ell=+1  thin_plate_3d  res={res}",
        )
        print(f"wrote {fig_path}")
        row["figure"] = str(fig_path)

    # One centered-index slab: n = 1.5 + 0.4 φ/π so negative phase is not vacuum.
    print("\n=== spiral thin_plate_3d res=16  slab_n0=1.5 (centered index) ===")
    try:
        meep_n0 = wb.simulate_fullwave(
            plate,
            backend="meep",
            L_max=4,
            grid_size=32,
            extent=3.5,
            resolution=16,
            layout="thin_plate_3d",
            pml=1.0,
            sz=6.0,
            until=40,
            slab_thickness=0.5,
            slab_n0=1.5,
            slab_dn=0.4,
        )
        vs_n0 = compare_spectra(modal, meep_n0)
        centered = {
            "resolution": 16,
            "layout": "thin_plate_3d",
            "slab_n0": 1.5,
            "slab_dn": 0.4,
            "dominant_ell": int(meep_n0.dominant_ell()),
            "expectation_ell": float(meep_n0.expectation_ell()),
            "purity": _purity(meep_n0),
            "cosine_vs_modal": vs_n0["cosine"],
            "dominant_match": vs_n0["dominant_match"],
            "extras": _jsonable(meep_n0.extras),
        }
        print(
            f"  ℓ={centered['dominant_ell']:+d}  P={centered['purity']:.3f}  "
            f"cosine={centered['cosine_vs_modal']:.3f}  match={centered['dominant_match']}"
        )
        fig_n0 = _fig_dir() / "spiral_thin_plate_res16_n0.png"
        plot_backend_spectra(
            [modal, meep_n0],
            expected_ell=1,
            path=str(fig_n0),
            title="spiral ell=+1  thin_plate_3d  res=16  n0=1.5",
        )
        centered["figure"] = str(fig_n0)
    except FullWaveUnavailable as exc:
        centered = {"resolution": 16, "slab_n0": 1.5, "error": str(exc)}
        print(f"  FAILED {exc}")

    payload = {
        "expected_ell": 1,
        "cell": {"extent": 3.5, "sz": 6.0, "pml": 1.0, "slab_thickness": 0.5},
        "note": (
            "Higher-res slab attempt. Previous negative: spiral res=12 extent=5 "
            "peaked at ℓ=−4, cosine 0.151. Charge-correct source-imprint is still "
            "the validated FDTD path unless a row here matches ℓ=+1."
        ),
        "modal": _summary(modal),
        "sweep": rows,
        "centered_index": centered,
    }
    _write_json(_fig_dir() / "thin_plate_3d_hires.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Meep validation suite")
    parser.add_argument(
        "cmd",
        nargs="?",
        default="all",
        choices=["sweep", "spiral", "slab", "cells", "slab-hires", "all"],
    )
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
    if args.cmd in {"cells", "all"}:
        cmd_cells(wb)
    if args.cmd == "slab-hires":
        cmd_slab_hires(wb, resolutions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
