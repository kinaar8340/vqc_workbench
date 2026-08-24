# Roadmap

## Done (Phase 0–1)

- Installable package + YAML configs + material library
- Structure API with 10 registered kinds
- Modal LG engine (structure → OAM spectrum)
- Helical VQC codec (payload bits on OAM carriers + repetition QEC)
- SLM export with hardware presets
- Streamlit dashboard + CLI
- Ecosystem probe over `~/Projects`
- Tests (structure, modal, pipeline, export, config)

## Done (Phase 2 interface)

- `FullWaveResult` (`ell`, coefficients, intensity, S/T) shared by all backends
- Structure-hash cache (memory, optional disk)
- `scalar` angular-spectrum backend (always on) vs modal side-by-side
- Meep / RCWA still fail loudly when the solver is not installed
- Matched-filter / cascade compensation for mode shifters
- Dashboard: identity vs structure vs compensated, ecosystem status panel
- Expected-ℓ readout (`winding − n_trenches` for trajectoids, etc.)
- Live Kolmogorov turbulence on the displayed OAM spectrum
- Primary **Compensate** button when the optic is a mode shifter
- Meep FDTD gated on `VQC_MEEP_RUN=1`; source-imprint DFT path
- Trajectoid three-column modal / scalar / Meep figure (`docs/figures/trajectoid_backend_spectra.png`)
- Source-imprint resolution sweep (16→32): cosine 0.884 → 0.986, always ℓ = −6
- Spiral plate ℓ = +1 Meep confirmation (purity 0.907, cosine 0.999)
- Dielectric slab (`thin_plate_3d`) documented as not yet charge-correct at affordable res

## Phase 2 remaining

- Real Meep 2-D/3-D runs for gratings and meta-atoms (`VQC_MEEP_RUN=1`)
- RCWA layer-stack mapping (grcwa / nannos) instead of the scalar stand-in
- Disk cache under `outputs/fullwave_cache/` wired through config

## Phase 3 — in progress

- Inverse-design loop (modal inner loop; charge / forecast / fidelity objectives)
- Live `oam_flux` lattice coupling (deposit + κ sweep + OAM back-action)
- Hardware-in-the-loop: SLM playlist → vqc_demo projector proxy
- Live `flux_trajectoid.generate_shell` instead of analytic trenches
- Keep qga theorems out of the physical hypotheses (docs-only)

## Non-goals

- Replacing Lumerical / OptoCompiler
- Importing `vqc_proto/src/photonics.py` (import-time side effects)
- Reverse imports from ecosystem packages into this one
