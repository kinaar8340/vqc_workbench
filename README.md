# vqc_workbench

VQC-native **photonic workbench**: define, edit, and simulate metamaterials,
gratings, Orbital Braille typeheads, trajectoid shells, and Hopf-lattice
defects, then push the resulting OAM content through a Vortex Quaternion
Conduit pipeline.

This is a research prototype, not a drop-in replacement for Lumerical /
Synopsys OptoCompiler. The fast path is a thin-element modal engine. Optional
Meep / RCWA backends are hooks for later validation.

## Install

```bash
cd ~/Projects/vqc_workbench
pip install -e .
pip install -e ".[ui,dev]"    # dashboard + tests
```

Optional neighbours (never required):

```bash
pip install -e ../flux_hopf_lib
pip install -e ../oam_flux
# vqc_proto, flux_trajectoid, hfb, vqc_demo — discovered if importable
```

## Quick start

```python
from vqc_workbench import Workbench

wb = Workbench()

grating = wb.create_grating(kind="spiral_phase", ell=3)
modes = wb.simulate_modes(grating, L_max=8)
print(modes.dominant_ell(), modes.coefficients)

result = wb.run_vqc(wb.create_structure("identity"), b"Hi")
print(result.fidelity, result.recovered_payload)

braille = wb.create_orbital_braille(n_orbs=4)
wb.export_slm(braille, "outputs/slm_phase.npy")
```

CLI:

```bash
vqc-workbench status
vqc-workbench simulate --kind spiral_phase --ell 3
vqc-workbench run-vqc --kind identity --payload Hi
vqc-workbench dashboard
```

## What is in the box

- Parametric structures: spiral phase plate, binary / blazed / forked
  gratings, metasurface phase maps, Orbital Braille, trajectoid trenches,
  flux-lattice vortex rings.
- YAML configs under `configs/` (global defaults, material library, examples).
- Modal OAM engine (LG projection + helical payload codec + turbulence).
- End-to-end `run_vqc` (encode → couple through a structure → propagate →
  repetition QEC → decode).
- SLM export (Holoeye / Meadowlark / Thorlabs presets).
- Streamlit editor.
- Full-wave skeletons (`MeepBackend`, `RCWABackend`) that fail loudly until
  the solver is installed.

See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md),
[docs/adding_a_structure.md](docs/adding_a_structure.md), and
[docs/ecosystem.md](docs/ecosystem.md).

## Phased roadmap

| Phase | Status |
|-------|--------|
| 0 Inventory + scaffolding + Structure → modes API | **this tree** |
| 1 Analytical gratings / metasurfaces + dashboard | **this tree** |
| 2 Meep / RCWA wrappers with cached S-matrices | skeleton only |
| 3 Inverse design, live oam_flux lattice, hardware-in-the-loop | later |

## License

MIT for the workbench integration layer. Optional VQC extras
(`vqc_proto`, `vqc_sims_public`) remain CC-BY-NC-SA-4.0 with patent
restrictions (US Prov. 63/913,110). See [IP_NOTICE.md](IP_NOTICE.md).

