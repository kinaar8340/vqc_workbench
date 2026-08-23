#!/usr/bin/env python3
"""Orbital Braille snapshot → modes + SLM export."""

from pathlib import Path

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    braille = wb.create_orbital_braille(n_orbs=4, duties=[0.25, 0.5, 0.75, 0.4])
    modes = wb.simulate_modes(braille, L_max=8)
    print(f"typehead dominant_ell={modes.dominant_ell()}  purity={float((modes.intensity**2).sum()):.3f}")
    out = Path("outputs/braille_slm")
    path = wb.export_slm(braille, out)
    print(f"SLM package → {path}")


if __name__ == "__main__":
    main()
