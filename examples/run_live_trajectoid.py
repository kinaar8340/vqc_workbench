#!/usr/bin/env python3
"""Compare analytic Jacobi–Anger trenches with live flux_trajectoid.generate_shell."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    analytic = wb.create_trajectoid(n_trenches=8, winding=2, payload_hash="vqc")
    live = wb.create_trajectoid(n_trenches=8, winding=2, payload_hash="vqc", live=True)
    a = wb.simulate_modes(analytic, L_max=8, grid_size=64)
    b = wb.simulate_modes(live, L_max=8, grid_size=64)
    spec = live.to_geometry_dict()
    shell = spec.get("shell") or {}
    print(
        f"analytic  dominant_ell={a.dominant_ell():+d}  ⟨ℓ⟩={a.expectation_ell():.2f}  "
        f"expected={wb.forecast_charge(analytic).expected_ell:+d}"
    )
    print(
        f"live      dominant_ell={b.dominant_ell():+d}  ⟨ℓ⟩={b.expectation_ell():.2f}  "
        f"mismatch={shell.get('mismatch_deg', float('nan')):.2f}°  "
        f"kx={shell.get('kx', float('nan')):.3f}  ky={shell.get('ky', float('nan')):.3f}"
    )
    print(wb.forecast_charge(live).formula)


if __name__ == "__main__":
    main()
