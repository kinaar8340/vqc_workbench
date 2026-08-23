"""Quickstart: load a YAML structure and print its OAM spectrum.

Run:  python notebooks/01_quickstart_structure.py
"""

from vqc_workbench import Workbench
from vqc_workbench.core.config import workbench_root

wb = Workbench()
path = workbench_root() / "configs" / "structures" / "spiral_phase.yaml"
plate = wb.load_structure(path)
modes = wb.simulate_modes(plate, L_max=8)
print("loaded", path.name, "dominant ℓ =", modes.dominant_ell())
