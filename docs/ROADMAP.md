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

## Phase 2 — full-wave (skeleton present)

- Real Meep 2-D/3-D runs for gratings and meta-atoms
- RCWA (grcwa / nannos) for periodic metasurfaces
- Cache S-matrix / modal coefficients so the fast VQC path stays usable
- Hand far-field OAM content from FDTD into `run_vqc`

## Phase 3 — unified workbench

- Inverse-design loop (alignment / string_optimizer scoring)
- Live `oam_flux` lattice coupling (gauge torque, κ/ℓ sweeps)
- Live `flux_trajectoid.generate_shell` instead of analytic trenches
- Hardware-in-the-loop: SLM playlist → vqc_demo projector proxy → camera decode
- Keep qga theorems out of the physical hypotheses (docs-only)

## Non-goals

- Replacing Lumerical / OptoCompiler
- Importing `vqc_proto/src/photonics.py` (import-time side effects)
- Reverse imports from ecosystem packages into this one
