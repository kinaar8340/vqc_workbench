# Inverse design

Phase 3 starts here. The optimizer searches a structure's parameter box
(from `ui/editors.py` schemas) using the **modal** engine as the inner loop.
Meep is for later validation of a candidate, not for every score.

## Objectives

| `objective` | What is minimized |
|-------------|-------------------|
| `charge` | `|dominant ℓ − target| + 0.25 |⟨ℓ⟩ − target| + (1 − purity)` |
| `forecast` | analytic `forecast_charge` error, then measured charge + purity |
| `fidelity` | `1 −` end-to-end `run_vqc` fidelity |

Integer parameters are enumerated (capped by `max_evals`). Charge/forecast
searches default to the integer fields only (`ell`, `n_trenches`, `winding`, …).

## API

```python
from vqc_workbench import Workbench

wb = Workbench()
hit = wb.inverse_design("trajectoid", objective="charge", target_ell=-6)
print(hit.params, hit.metrics["dominant_ell"], hit.metrics["purity"])

hit = wb.inverse_design("spiral_phase", objective="forecast", target_ell=2)
```

## CLI

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli inverse --kind trajectoid --target-ell -6
PYTHONPATH=src python3 -m vqc_workbench.cli inverse --kind spiral_phase --target-ell 3 --objective forecast
PYTHONPATH=src python3 -m vqc_workbench.cli inverse --kind binary_grating --objective fidelity --payload Hi
```

The inner loop does not call Meep. After you have a candidate, validate it:

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli simulate --kind trajectoid --n-trenches N --winding W
# optional:
# VQC_MEEP_RUN=1 ... compare --kind trajectoid --backends modal,scalar,meep
```
