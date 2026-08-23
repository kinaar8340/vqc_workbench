#!/usr/bin/env python3
"""Spiral phase plate → OAM spectrum."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    grating = wb.create_grating(kind="spiral_phase", ell=3)
    modes = wb.simulate_modes(grating, L_max=8)
    print(f"structure={grating.kind}  dominant_ell={modes.dominant_ell()}")
    for ell, intensity in zip(modes.ell, modes.intensity):
        if intensity > 0.02:
            print(f"  ℓ={int(ell):+d}  I={intensity:.3f}")


if __name__ == "__main__":
    main()
