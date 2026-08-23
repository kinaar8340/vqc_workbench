# Adding a structure

1. Create `src/vqc_workbench/structures/my_cell.py`.
2. Subclass `ParametricCell` and decorate with `@register("my_kind")`.
3. Implement `to_phase_mask(self, grid, wavelength_nm)`.
4. Optionally override `to_geometry_dict` for Meep / RCWA.
5. Export the class from `structures/__init__.py`.
6. Add a YAML example under `configs/structures/`.
7. Add a slider schema in `ui/editors.py`.
8. Add a test that checks the mask (and, if relevant, dominant ℓ).

```python
from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell
from vqc_workbench.utils.grid import polar_from_cartesian
import numpy as np

@register("axicon")
class Axicon(ParametricCell):
    kind = "axicon"

    def __init__(self, name="axicon", params=None, material=None):
        params = dict(params or {})
        params.setdefault("alpha", 0.4)
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float):
        x, y = grid
        rho, _ = polar_from_cartesian(x, y)
        return np.exp(1j * float(self.params["alpha"]) * rho)
```

Then:

```python
from vqc_workbench import Workbench
wb = Workbench()
cell = wb.create_structure("axicon", alpha=0.5)
wb.simulate_modes(cell)
```

Keep new cells **thin-element first**. Full-wave geometry belongs in
`to_geometry_dict()`, consumed later by `simulation/fullwave.py`.
