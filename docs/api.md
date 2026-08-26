# API

```python
from vqc_workbench import Workbench

wb = Workbench()                          # loads configs/default.yaml
wb = Workbench("configs/default.yaml")
```

## Structures

```python
g = wb.create_grating(kind="spiral_phase", ell=3)
g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
g = wb.create_grating(kind="forked_hologram", ell=2, period=0.35)
b = wb.create_orbital_braille(n_orbs=4, duties=[0.25, 0.5, 0.75, 0.4])
t = wb.create_trajectoid(payload_hash="vqc", winding=2)
t = wb.create_trajectoid(payload_hash="vqc", winding=2, live=True)  # flux_trajectoid.generate_shell
m = wb.create_metasurface(ell_target=1)
f = wb.create_flux_lattice(ell=3, n_sites=8, kappa=0.85)
i = wb.create_structure("identity")
s = wb.load_structure("configs/structures/spiral_phase.yaml")

g2 = g.update(ell=5)                      # immutable copy
g.to_yaml("out.yaml")

fc = wb.forecast_charge(t)
print(fc.expected_ell, fc.formula)        # -6,  ℓ = winding − n_trenches …
```

Kinds: `spiral_phase`, `binary_grating`, `blazed_grating`, `forked_hologram`,
`metasurface`, `orbital_braille`, `trajectoid`, `flux_lattice`, `custom`,
`identity`, `matched_filter`, `cascade`.

Every structure implements:

- `to_phase_mask((x, y), wavelength_nm) -> complex ndarray`
- `to_geometry_dict() -> dict` (full-wave / YAML)
- `update(**params) -> Structure`

## Simulation

```python
modes = wb.simulate_modes(g, L_max=8)
print(modes.dominant_ell(), modes.coefficients)

prop = wb.modal.propagate(modes, z_range=(0, 5), turbulence=0.2, n_z=40)

result = wb.run_vqc(i, b"Hi", L_max=8, qec_reps=1, turbulence=0.0)

# photonic ladder HMI (Streamlit; needs [ui])
# wb.launch_ladder(port=8502)
from vqc_workbench.ladder import LadderEngine, beam_evolution_ladder
doc = beam_evolution_ladder()
rt = LadderEngine(workbench=wb, grid_size=64).bind(doc)
print(result.fidelity, result.ber, result.recovered_payload)
```

`run_vqc` auto-raises `L_max` so the payload fits (2 bits per non-zero ℓ).
A spiral / forked hologram is a mode shifter — use `identity`, or compensate:

```python
# inverse thin-element of a known optic
filt = wb.matched_filter(g)
channel = wb.compensate(g)          # g then filt  ≈ identity
result = wb.run_vqc(g, b"Hi", compensate=True)

modal_vs_scalar = wb.compare_backends(g, ("modal", "scalar"), z=0.0)
fw = wb.simulate_fullwave(g, backend="scalar")
# Meep: layout="source_imprint" (charge-correct) or "thin_plate_3d"
# RCWA: backend="rcwa"  (pip install grcwa)
# Disk cache: outputs/fullwave_cache/  (VQC_FULLWAVE_CACHE=0 to disable)
```

## Export

```python
wb.export_slm(b, "outputs/slm_phase.npy", device="holoeye_pluto_2")
wb.export_hologram_stack(b, "outputs/stack", n_frames=8)
hit = wb.hitl("I live in Oregon", g, channel="projector", out="outputs/hitl")
```

Presets: `generic_512`, `holoeye_pluto_2`, `meadowlark_512`, `thorlabs_1080p`.

## CLI

```bash
vqc-workbench status
vqc-workbench simulate --kind spiral_phase --ell 3
vqc-workbench simulate --kind trajectoid --n-trenches 8 --winding 2 --live
vqc-workbench run-vqc --kind identity --payload Hi
vqc-workbench run-vqc --kind spiral_phase --ell 3 --payload Hi --compensate
vqc-workbench compare --kind binary_grating --backends modal,scalar
vqc-workbench compare --kind binary_grating --backends modal,rcwa
vqc-workbench export-slm --kind orbital_braille --out outputs/slm
vqc-workbench inverse --kind trajectoid --target-ell -6
vqc-workbench couple --kind spiral_phase --ell 3 --kappa 0.85 --steps 8
vqc-workbench couple --kind trajectoid --sweep-kappa 0.80,0.85,0.89 --steps 4 --json
vqc-workbench hitl --payload "I live in Oregon" --kind spiral_phase --ell 3 --channel projector
vqc-workbench dashboard --port 8501
```

## Dashboard

```python
wb.launch_dashboard()
# or: pip install vqc-workbench[ui] && vqc-workbench dashboard
```
