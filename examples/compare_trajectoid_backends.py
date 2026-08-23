#!/usr/bin/env python3
"""Modal / scalar / Meep OAM spectra for the canonical trajectoid.

    VQC_MEEP_RUN=1 PYTHONPATH=src python examples/compare_trajectoid_backends.py

Writes docs/figures/trajectoid_backend_spectra.png and a JSON sidecar.
Meep is optional: without it the figure is modal+scalar and the Meep panel
is annotated as unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path

from vqc_workbench import Workbench
from vqc_workbench.core.config import workbench_root
from vqc_workbench.simulation.fullwave import FullWaveUnavailable
from vqc_workbench.ui.visualizers import plot_backend_spectra


def _summary(result) -> dict:
    purity = float((result.intensity**2).sum())
    return {
        "backend": result.backend,
        "dominant_ell": int(result.dominant_ell()),
        "expectation_ell": float(result.expectation_ell()),
        "purity": purity,
        "extras": {k: v for k, v in result.extras.items() if isinstance(v, (str, int, float, bool, type(None)))},
    }


def main() -> int:
    wb = Workbench()
    shell = wb.create_trajectoid(n_trenches=8, winding=2)
    expected = wb.forecast_charge(shell).expected_ell
    kw = dict(L_max=8, grid_size=40, w0=1.0, extent=4.5)

    results = []
    notes: dict[str, str] = {}
    for name, extra in (("modal", {}), ("scalar", {"z": 0.0}), ("meep", {"resolution": 16})):
        try:
            results.append(wb.simulate_fullwave(shell, backend=name, **kw, **extra))
        except FullWaveUnavailable as exc:
            notes[name] = str(exc)
            print(f"{name}: UNAVAILABLE — {exc}")

    if len(results) < 2:
        raise SystemExit("need at least modal+scalar to build a figure")

    root = workbench_root()
    fig_dir = root / "docs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path = fig_dir / "trajectoid_backend_spectra.png"
    json_path = fig_dir / "trajectoid_backend_spectra.json"

    plot_backend_spectra(
        results,
        expected_ell=expected,
        path=str(fig_path),
        title=f"trajectoid n=8, w=2  →  expected ℓ = {expected:+d}",
    )

    payload = {
        "expected_ell": expected,
        "formula": wb.forecast_charge(shell).formula,
        "backends": [_summary(r) for r in results],
        "unavailable": notes,
    }
    if len(results) >= 2:
        from vqc_workbench.simulation.compare import compare_many, compare_spectra

        if len(results) == 2:
            cmp = compare_spectra(results[0], results[1])
            payload["pairwise"] = [
                {
                    "a": cmp["backend_a"],
                    "b": cmp["backend_b"],
                    "cosine": cmp["cosine"],
                    "dominant_match": cmp["dominant_match"],
                }
            ]
        else:
            many = compare_many(results)
            payload["pairwise"] = many["pairwise"]

    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {fig_path}")
    print(f"wrote {json_path}")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
