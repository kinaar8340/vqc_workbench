# Meep validation

Companion to [trajectoid.md](trajectoid.md). All FDTD numbers below were
produced with pymeep 1.34 in the `vqc-meep` conda env.

```bash
conda activate vqc-meep
VQC_MEEP_RUN=1 PYTHONPATH=src python examples/meep_validation.py all
```

## 1. Trajectoid resolution sweep (source-imprint)

Canonical cell: `n_trenches=8`, `winding=2`, expected ℓ = −6.
Layout: Gaussian × mask source, 3-D vacuum, DFT Ez downstream.

| res | Dominant ℓ | Purity | cosine vs modal |
|-----|------------|--------|-----------------|
| 16 | −6 | 0.437 | 0.884 |
| 20 | −6 | 0.517 | 0.905 |
| 24 | −6 | 0.604 | 0.953 |
| 32 | −6 | 0.734 | 0.986 |

The charge is correct at every resolution. Purity and cosine tighten
monotonically; res=32 is already publication-usable for the charge claim
(cosine 0.986) even though purity is still 0.73 because of ℓ = −7 leakage.

![Purity and cosine vs Meep resolution](figures/trajectoid_meep_resolution_sweep.png)

## 2. Spiral phase plate, ℓ = +1 (source-imprint)

Cheaper cell (`res=12`, extent 3.5). All three backends peak at +1.

![Spiral modal / scalar / Meep](figures/spiral_backend_spectra.png)

| Backend | Dominant ℓ | Purity | cosine vs modal |
|---------|------------|--------|-----------------|
| modal | +1 | 1.000 | — |
| scalar | +1 | 1.000 | 1.000 |
| meep (source-imprint, res=12) | +1 | 0.907 | 0.999 |

|ℓ| = 1 is easy for FDTD: almost no neighbor leakage.

## 3. Dielectric slab (`layout=thin_plate_3d`)

Larger cell and thicker PML (pml=1.2, sz=8). The slab is a true ε(x,y)
MaterialGrid, **not** a source imprint. At the resolutions we can afford
here it does **not** recover the topological charge.

| Cell | res | Expected ℓ | Meep dominant ℓ | cosine vs modal |
|------|-----|------------|-----------------|-----------------|
| spiral ell=+1, extent=5 | 12 | +1 | −4 | 0.151 |
| trajectoid n=8 w=2, extent=6 | 16 | −6 | +8 | 0.006 |

That is an honest negative: a 0.5-thick slab at these pixel counts cannot
hold the helical phase. Source-imprint remains the validated FDTD path.
Raising slab resolution into the 32–48 range (with this cell) is the next
Meep-only experiment, not a Phase 3 item.

JSON: [`figures/thin_plate_3d.json`](figures/thin_plate_3d.json).
