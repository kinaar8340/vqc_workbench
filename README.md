# vqc_workbench

VQC-native **photonic workbench**: define, edit, and simulate metamaterials,
gratings, Orbital Braille typeheads, trajectoid shells, and Hopf-lattice
defects, then push the resulting OAM content through a Vortex Quaternion
Conduit pipeline.

This is a research prototype, not a drop-in replacement for Lumerical /
Synopsys OptoCompiler. The fast path is a thin-element modal engine. A
scalar-diffraction full-wave lite is always on; Meep / RCWA backends fail
loudly until those solvers are installed.

Workbench **imports** the kinaar8340 stack (`oam_flux`, `vqc_demo`,
`flux_trajectoid`, …). Those packages must never import this one.
`vqc_proto/src/photonics.py` is not imported (import-time side effects).

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
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --render docs/figures/ladder_hmi.png
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --preset slm_playlist --il
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --port 8502   # PLC-style photonic ladder HMI
PYTHONPATH=src python3 -m vqc_workbench.cli inverse --kind trajectoid --target-ell -6
PYTHONPATH=src python3 -m vqc_workbench.cli couple --kind spiral_phase --ell 3 --kappa 0.85 --steps 8
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload Hi --kind spiral_phase --channel projector
PYTHONPATH=src python3 -m vqc_workbench.cli simulate --kind trajectoid --live --payload-hash vqc
```

`status` lists neighboring checkouts under `~/Projects`. `simulate` prints the
OAM spectrum (including **expected ℓ** from the structure parameters).
`run-vqc` on `identity` should recover `Hi` at fidelity 1.0.

A trajectoid with 8 trenches and winding 2 piles onto ℓ = −6
(`winding − n_trenches`). Walkthrough:
[docs/trajectoid.md](docs/trajectoid.md).

Optional FDTD (conda env `vqc-meep`, pymeep 1.34), gated on `VQC_MEEP_RUN=1`:

```bash
# VQC_MEEP_RUN=1 PYTHONPATH=src python examples/compare_trajectoid_backends.py
# VQC_MEEP_RUN=1 PYTHONPATH=src python examples/meep_validation.py all
```

Validated Meep **source-imprint** cells: trajectoid ℓ = −6 (res 16→32),
spiral ℓ = +1, and metasurface `ell_target=+1`. Binary / blazed / forked
agree with the modal projector in spectral shape. Dielectric slab
(`thin_plate_3d`) at res=12 with Ex and a 0.7λ n(x,y) plate **peaks at
ℓ=+1** (cosine 0.709). See [docs/meep_validation.md](docs/meep_validation.md).

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
pip install -e ../vqc_demo
pip install -e ../flux_trajectoid
# vqc_proto, hfb — discovered if importable
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

# live ecosystem adapters (skip if the package is missing)
wb.couple_to_lattice(grating, kappa=0.85, steps=8, ell=3)
wb.hitl("Hi", grating, channel="projector")
live = wb.create_trajectoid(payload_hash="vqc", winding=2, live=True)
```

CLI:

```bash
vqc-workbench status
vqc-workbench simulate --kind spiral_phase --ell 3
vqc-workbench run-vqc --kind identity --payload Hi
vqc-workbench couple --kind spiral_phase --ell 3
vqc-workbench hitl --payload Hi --channel projector
vqc-workbench dashboard
vqc-workbench ladder --render docs/figures/ladder_hmi.png
vqc-workbench ladder
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
- Streamlit editor plus a PLC-style photonic ladder HMI
  ([docs/ladder.md](docs/ladder.md), `vqc-workbench ladder`).
- Full-wave interface (`FullWaveResult` + structure-hash cache): `scalar`
  angular-spectrum always available; `meep` / `rcwa` fail loudly if missing.
  `rcwa` is a real layer stack (grcwa / nannos), not a scalar stand-in
  ([docs/rcwa.md](docs/rcwa.md)).
- Matched-filter / cascade helper so a known mode shifter can recover payload.
- Inverse design: search structure parameters for a target ℓ or VQC fidelity
  ([docs/inverse.md](docs/inverse.md)).
- Live `oam_flux` lattice coupling ([docs/lattice.md](docs/lattice.md)).
- Hardware-in-the-loop: SLM playlist → vqc_demo projector proxy
  ([docs/hitl.md](docs/hitl.md)).
- Live `flux_trajectoid.generate_shell` trenches (`create_trajectoid(live=True)`);
  analytic Jacobi–Anger cell remains the default.

See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md),
[docs/adding_a_structure.md](docs/adding_a_structure.md), and
[docs/ecosystem.md](docs/ecosystem.md).

## Phased roadmap

| Phase | Status |
|-------|--------|
| 0 Inventory + scaffolding + Structure → modes API | **this tree** |
| 1 Analytical gratings / metasurfaces + dashboard | **this tree** |
| 2 Full-wave interface, cache, scalar diffraction, matched filter | **this tree** (Meep source-imprint + charge-correct slab; RCWA layer stack) |
| 3 Inverse design, oam_flux lattice, HITL, live generate_shell | **this tree** |
| 4 Photonic ladder HMI (PLC / lab mapping, dual beam monitors) | **this tree** |

Phase 2 remaining: none of the original interface items. Disk cache is on
(`outputs/fullwave_cache/`). Details:
[docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT for the workbench integration layer. Optional VQC extras
(`vqc_proto`, `vqc_sims_public`) remain CC-BY-NC-SA-4.0 with patent
restrictions (US Prov. 63/913,110). See [IP_NOTICE.md](IP_NOTICE.md).
