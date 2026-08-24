# Live oam_flux lattice coupling

The photonic side stays in the workbench modal engine. [oam_flux](https://github.com/kinaar8340/oam_flux)
owns the gauged Hopf lattice, flywheel deposition, gauge torque (κ), and
back-reaction.

```
structure / ModeResult
        │  simulate_modes + propagate
        ▼
OAM intensity(z, ℓ) + LG radial weights
        │  deposit_on_flywheels
        ▼
TwistLattice  (κ ⟨θ⟩ gauge + flywheel kick)
        │  lattice_back_reaction
        ▼
updated ⟨θ⟩, coupling_factor, Δℓ  →  leaked OAM spectrum
```

`oam_flux` is imported if installed, otherwise `~/Projects/oam_flux/src` is
added to `sys.path`. Missing the package raises `LatticeUnavailable`.

## API

```python
from vqc_workbench import Workbench

wb = Workbench()
plate = wb.create_grating(kind="spiral_phase", ell=3)
hit = wb.couple_to_lattice(plate, kappa=0.85, steps=8, nx=12, ell=3)
print(hit.final_mean_twist, hit.coupling_factor, hit.ell_shift)
print(hit.oam_before, hit.oam_after)

sweep = wb.couple_to_lattice(plate, steps=4, sweep_kappa=[0.80, 0.85, 0.89])
```

## CLI

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli couple --kind spiral_phase --ell 3 --kappa 0.85 --steps 8
PYTHONPATH=src python3 -m vqc_workbench.cli couple --kind trajectoid --sweep-kappa 0.80,0.85,0.89 --steps 4
PYTHONPATH=src python3 -m vqc_workbench.cli couple --kind spiral_phase --ell 3 --json
```

Default CLI is a one-screen summary (`⟨θ⟩`, κ_eff, Δℓ, residual, OAM before/after,
pump vs recovery). Pass `--json` for the full per-step history dump.

The inner loop is modal (fast). Use a small `nx` (8–16) for interactive
sweeps; oam_flux defaults to 24 in its own demos.
