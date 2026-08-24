#!/usr/bin/env python3
"""RCWA layer stack vs modal thin-element on a binary grating."""

from vqc_workbench import Workbench
from vqc_workbench.simulation.fullwave import FullWaveUnavailable


def main() -> None:
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    modal = wb.simulate_fullwave(g, backend="modal", L_max=4, grid_size=32)
    try:
        rcwa = wb.simulate_fullwave(g, backend="rcwa", L_max=4, grid_size=32, nG=21)
    except FullWaveUnavailable as exc:
        print(f"RCWA unavailable: {exc}")
        return
    print(
        f"modal  ℓ={modal.dominant_ell():+d}  ⟨ℓ⟩={modal.expectation_ell():.3f}"
    )
    print(
        f"rcwa   engine={rcwa.extras.get('engine')}  "
        f"R={rcwa.extras.get('R_total'):.3f}  T={rcwa.extras.get('T_total'):.3f}  "
        f"ℓ={rcwa.dominant_ell():+d}"
    )
    print(rcwa.extras.get("note"))


if __name__ == "__main__":
    main()
