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
│  create_* · simulate_modes · run_vqc · export_slm            │
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
   channel. A spiral plate *should* scramble that payload (mode shifter).

## Backends

- **modal** (default): thin-element phase mask + LG / helical projection +
  vectorized z-propagation with optional Kolmogorov mixing.
- **meep / rcwa**: opt-in skeletons in `simulation/fullwave.py`. They raise
  `FullWaveUnavailable` until the solver is installed. Results are meant to
  feed the same `coefficients` dict the modal path already consumes.

## Config

`configs/default.yaml` is the single source of truth for `L_max`, λ, grid,
QEC, SLM device, and lattice κ. The UI, CLI, and Python API all load it.
