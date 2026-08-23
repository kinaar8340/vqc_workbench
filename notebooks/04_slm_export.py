"""Export a spiral phase plate as an SLM phase package."""

from pathlib import Path

from vqc_workbench import Workbench

wb = Workbench()
plate = wb.create_grating(kind="spiral_phase", ell=1)
out = wb.export_slm(plate, Path("outputs/slm_notebook"), device="generic_512")
print("wrote", out)
