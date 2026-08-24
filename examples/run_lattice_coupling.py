#!/usr/bin/env python3
"""Deposit a spiral-plate OAM mode onto an oam_flux Hopf lattice."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    result = wb.couple_to_lattice(plate, kappa=0.85, steps=8, nx=12, ell=3)
    print(
        f"ℓ={result.ell}  κ={result.kappa}  "
        f"⟨θ⟩ {result.initial_mean_twist:.4f} → {result.final_mean_twist:.4f}  "
        f"κ_eff={result.coupling_factor:.3f}  Δℓ={result.ell_shift:.4f}"
    )
    sweep = wb.couple_to_lattice(
        plate, steps=4, nx=12, ell=3, sweep_kappa=[0.80, 0.85, 0.89]
    )
    for row in sweep.sweep or []:
        print(
            f"  κ={row['kappa']:.2f}  ⟨θ⟩={row['final_mean_twist']:.4f}  "
            f"κ_eff={row['coupling_factor']:.3f}"
        )


if __name__ == "__main__":
    main()
