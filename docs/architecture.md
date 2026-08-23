# Architecture

`vqc_workbench` is a **VQC-native photonic workbench**: a structure editor and
simulation shell that sits *on top of* the existing kinaar8340 stack rather
than replacing commercial PDA tools (Lumerical, OptoCompiler, …).

```
┌─────────────────────────────────────────────────────────────┐
│  UI / CLI / notebooks                                        │
│  Streamlit dashboard · vqc-workbench CLI · examples/         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│  Workbench façade (api.py)                                   │
│  create_* · simulate_modes · simulate_fullwave · run_vqc     │
└──────────────┬─────────────────────────────┬────────────────┘
               │                             │
     ┌─────────▼─────────┐         ┌─────────▼─────────┐
     │ Structure layer   │         │ Simulation layer  │
     │ grating / meta /  │  mask   │ Modal (always)    │
     │ braille / shell / │ ──────► │ Full-wave (opt)   │
     │ flux lattice      │         │ VQC pipeline      │
     └─────────┬─────────┘         └─────────┬─────────┘
               │                             │
               │ YAML + MaterialLibrary      │ encode → couple →
               │                             │ propagate → QEC →
               │                             │ decode
               ▼                             ▼
     flux_hopf_lib (optional)      oam_flux / vqc_proto / hfb
                                   (optional adapters)
```

## Dependency direction

`vqc_workbench` imports the ecosystem. **Never the reverse.**

| Package | Role | Required? |
|---------|------|-----------|
| numpy / scipy / pyyaml | core | yes |
| flux_hopf_lib | quaternion / Hopf fingerprint | optional (local fallback) |
| oam_flux | lattice coupling, vectorized photonics | optional |
| vqc_proto | Orbital Braille typehead, SLM playlist | optional (local geometry) |
| flux_trajectoid | 3-D rolling shells | optional (analytic trenches) |
| hfb | vortex-ring SLM / analog gravity | optional |
| qga | geometric design rules (docs / later) | optional |
| Meep / RCWA | full-wave validation | optional extras |

`vqc_proto/src/photonics.py` is **not** imported: it has import-time I/O
(prints `L_max`, loads YAML). The workbench uses a side-effect-free SciPy
LG / helical engine that matches `oam_flux.vqc_photonics`.

## Two projectors

1. **LG projector** (`simulation/lg.py`, `ModalSimulator.structure_to_modes`) —
   answers “what OAM content does this grating / metasurface generate from a
   Gaussian beam?”
2. **Helical codec projector** (`project_helical_spectrum`) — packs payload
   bits onto `exp(iℓφ)` carriers so `run_vqc` round-trips on an identity
   channel. A spiral plate *should* scramble that payload (mode shifter)
   unless `compensate=True` applies a matched filter.

## Backends

Every full-wave backend returns a `FullWaveResult` (`ell`, `coefficients`,
`intensity`, optional `S` / `T`) so the VQC pipeline does not care which
solver produced the numbers. Results are cached by a SHA-256 of
`(kind, params, backend, L_max, λ, grid)`.

- **modal** (default): thin-element phase mask + LG / helical projection +
  vectorized z-propagation with optional Kolmogorov mixing.
- **scalar**: angular-spectrum scalar diffraction (always available). At
  `z=0` it matches modal; a small `z` adds Fresnel diffraction.
- **meep / rcwa**: opt-in. Raise `FullWaveUnavailable` until the solver is
  importable. When present they still emit `FullWaveResult`.

Compare with `Workbench.compare_backends(structure, ("modal", "scalar"))`.

Meep is opt-in: `simulate_fullwave(..., backend="meep")` raises until
`VQC_MEEP_RUN=1` and MIT Meep is importable. Default layout is
**source-imprint**: complex amp = Gaussian × mask, 3-D vacuum FDTD, DFT Ez
on a downstream plane, then the same LG projector. `layout=thin_plate_3d`
is a dielectric slab (higher resolution required for |ℓ| ≳ 3). Tests skip
FDTD unless the env var is set. Canonical figure:
`docs/figures/trajectoid_backend_spectra.png`.

## Expected topological charge

`forecast_charge(structure)` turns parameters into an expected ℓ so the UI
can show the arithmetic next to the measured peak:

| Kind | Formula |
|------|---------|
| `spiral_phase` | `ell` |
| `trajectoid` | `winding − n_trenches` (Jacobi–Anger k = −1 branch) |
| `forked_hologram` | `ell` (after demodulating the linear carrier) |
| `identity` / 1-D gratings | `0` |

## Config

`configs/default.yaml` is the single source of truth for `L_max`, λ, grid,
QEC, SLM device, and lattice κ. The UI, CLI, and Python API all load it.
