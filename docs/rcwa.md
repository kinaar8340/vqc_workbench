# RCWA layer stack

The `rcwa` backend maps a workbench structure onto a three-layer stack and
solves it with [grcwa](https://github.com/weiliangjinca/grcwa) (preferred)
or [nannos](https://github.com/benvial/nannos). It emits the same
`FullWaveResult` as modal / scalar / Meep. It does **not** fall back to
the scalar angular-spectrum stand-in.

```
structure (period or phase map)
        │  structure_to_stack
        ▼
superstrate (n=1) / patterned slab ε(x,y) / substrate (n=1)
        │  grcwa or nannos  (planewave, nG orders)
        ▼
reconstructed E × Gaussian envelope → pack_oam_result
```

Install:

```bash
pip install grcwa          # lightweight, default engine
pip install nannos         # optional second engine
# or: pip install -e ".[rcwa]"
```

Missing both packages raises `FullWaveUnavailable`.

## Mapping

| Kind | Unit cell | Pattern |
|------|-----------|---------|
| `binary_grating`, `blazed_grating` | one grating `period` | duty / sawtooth ε between `n_lo` and `n_hi` |
| spiral, forked, metasurface, … | supercell `2*extent` | thin-element phase mapped to n(x,y) |

Slab thickness is `d = φ λ / (2π Δn)` from `depth_rad` unless you pass
`slab_thickness`. Length units match the scalar backend (`λ = max(λ_nm·1e-6, 0.05)`).

Illumination is a **normal-incidence planewave**. OAM coefficients are the
LG projection of the reconstructed transmitted field times a Gaussian
envelope. For 1-D gratings that is the right tool (diffraction orders,
R+T ≈ 1). A spiral plate in a supercell is **not** a charge-correct
substitute for Meep source-imprint — RCWA sees a periodic array of
plates, so the 0-order beam dominates.

## API

```python
from vqc_workbench import Workbench

wb = Workbench()
g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
hit = wb.simulate_fullwave(g, backend="rcwa", L_max=4, nG=21)
print(hit.extras["engine"], hit.extras["R_total"], hit.extras["T_total"])
# engine="nannos" to force the second solver
```

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli compare --kind binary_grating --backends modal,rcwa
PYTHONPATH=src python examples/run_rcwa.py
```
