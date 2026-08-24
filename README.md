# vqc_workbench

VQC-native **photonic workbench**: define, edit, and simulate metamaterials,
gratings, Orbital Braille typeheads, trajectoid shells, and Hopf-lattice
defects, then push the resulting OAM content through a Vortex Quaternion
Conduit pipeline.

This is a research prototype, not a drop-in replacement for Lumerical /
Synopsys OptoCompiler. The fast path is a thin-element modal engine. A
scalar-diffraction full-wave lite is always on; Meep / RCWA backends fail
loudly until those solvers are installed.

## First 10 minutes

From the repo root (with the package on `PYTHONPATH` or `pip install -e .`):

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli status
PYTHONPATH=src python3 -m vqc_workbench.cli simulate --kind spiral_phase --ell 3
PYTHONPATH=src python3 -m vqc_workbench.cli run-vqc --kind identity --payload Hi
```

A spiral plate is a **mode shifter**, so the same payload through the grating
does not round-trip until you compensate with a matched filter:

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli run-vqc --kind spiral_phase --ell 3 --payload Hi --compensate
PYTHONPATH=src python3 -m vqc_workbench.cli compare --kind binary_grating --backends modal,scalar
PYTHONPATH=src python3 -m vqc_workbench.cli dashboard   # needs: pip install -e ".[ui]"
# optional FDTD (conda env vqc-meep, pymeep 1.34):
# VQC_MEEP_RUN=1 PYTHONPATH=src python examples/compare_trajectoid_backends.py
PYTHONPATH=src python3 -m vqc_workbench.cli inverse --kind trajectoid --target-ell -6
```

`status` lists neighboring checkouts under `~/Projects`. `simulate` prints the
OAM spectrum (including **expected ℓ** from the structure parameters).
`run-vqc` on `identity` should recover `Hi` at fidelity 1.0.

A trajectoid with 8 trenches and winding 2 piles onto ℓ = −6
(`winding − n_trenches`). Walkthrough with the dashboard screenshot:
[docs/trajectoid.md](docs/trajectoid.md).

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
- Full-wave interface (`FullWaveResult` + structure-hash cache): `scalar`
  angular-spectrum always available; `meep` / `rcwa` fail loudly if missing.
- Matched-filter / cascade helper so a known mode shifter can recover payload.
- Inverse design: search structure parameters for a target ℓ or VQC fidelity
  ([docs/inverse.md](docs/inverse.md)).
- Live `oam_flux` lattice coupling ([docs/lattice.md](docs/lattice.md)).

See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md),
[docs/adding_a_structure.md](docs/adding_a_structure.md), and
[docs/ecosystem.md](docs/ecosystem.md).

## Phased roadmap

| Phase | Status |
|-------|--------|
| 0 Inventory + scaffolding + Structure → modes API | **this tree** |
| 1 Analytical gratings / metasurfaces + dashboard | **this tree** |
| 2 Full-wave interface, cache, scalar diffraction, matched filter | **this tree** (Meep/RCWA still opt-in) |
| 3 Inverse design, live oam_flux lattice, hardware-in-the-loop | later |

## License

MIT for the workbench integration layer. Optional VQC extras
(`vqc_proto`, `vqc_sims_public`) remain CC-BY-NC-SA-4.0 with patent
restrictions (US Prov. 63/913,110). See [IP_NOTICE.md](IP_NOTICE.md).

