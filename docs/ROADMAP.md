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

## Phase 2 remaining

- Real Meep 2-D/3-D runs for gratings and meta-atoms (`VQC_MEEP_RUN=1`)
- RCWA layer-stack mapping (grcwa / nannos) instead of the scalar stand-in
- Disk cache under `outputs/fullwave_cache/` wired through config

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
