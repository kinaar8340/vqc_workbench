#!/usr/bin/env python3
"""Find a trajectoid (n, w) whose measured OAM is ℓ = −6."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    result = wb.inverse_design(
        "trajectoid",
        objective="charge",
        target_ell=-6,
        L_max=8,
        grid_size=64,
    )
    print(result.as_dict())
    structure = wb.create_structure("trajectoid", **result.params)
    modes = wb.simulate_modes(structure, L_max=8)
    print(f"measured dominant ℓ = {modes.dominant_ell():+d}  purity = {(modes.intensity**2).sum():.3f}")


if __name__ == "__main__":
    main()
