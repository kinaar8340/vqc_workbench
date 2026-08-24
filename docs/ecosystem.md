# Ecosystem map

Local checkouts under `~/Projects` that this workbench is designed to sit
beside (GitHub: [kinaar8340](https://github.com/kinaar8340)).

## Simulation / hardware path

| Repo | What the workbench reuses |
|------|---------------------------|
| **vqc_proto** | Orbital Braille typehead, SLM hologram export, quaternion–OAM coupling, QEC stubs. Local PWM geometry is inlined so the workbench runs without it. |
| **vqc** / **vqc_sims_public** | `photonics.py` vectorized multi-ℓ propagation + Kolmogorov screens. **Not imported** (import-time side effects); logic ported to `simulation/modal.py`. |
| **vqc_demo** | Projector+camera intensity proxy, SLM presets, CRC / majority QEC. Live HITL via `Workbench.hitl` ([docs/hitl.md](hitl.md)). Device table copied into `export/slm.py`. |
| **oam_flux** | Helical packets on a gauged Hopf lattice, `PhotonicsConfig` / `propagate_multi_ell_vectorized`. Live coupling via `couple_to_lattice`. |
| **flux_trajectoid** | Trajectoid shells + phase trenches + SLM package. Live `generate_shell` via `create_trajectoid(live=True)`; analytic Jacobi–Anger trenches otherwise ([docs/trajectoid.md](trajectoid.md)). |
| **hfb** | Flux-bubble vortex arrays, `optics/slm_export.py`, VQC-proto bridge pattern (copied as `adapters.py`). |

## Geometry / theory (kept separate from physical hypotheses)

| Repo | Role |
|------|------|
| **flux_hopf_lib** | Single source of truth for quaternion algebra, Hopf maps, flux lattices. Optional import in `core/geometry.py`. |
| **qga** | Pedagogical Hopf / gauged-lattice book. Design rules, not a runtime dep. |
| **toe**, **kingdom_come**, **vortex_math**, **invariant_hunt**, **convex_defect** | Medium physics, portals, invariants — constrain metamaterial choices later. |
| **pic / qvpic** | Persistent-identity conduits; future “memory” layer for adaptive design. |
| **alignment**, **string_optimizer** | Inverse-design / scoring later. |

## Probe

```bash
vqc-workbench status
```

or

```python
from vqc_workbench.adapters import probe_ecosystem
print(probe_ecosystem().as_dict())
```
