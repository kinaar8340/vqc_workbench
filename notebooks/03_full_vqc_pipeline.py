"""Identity channel VQC round-trip (encode → propagate → QEC → decode)."""

from vqc_workbench import Workbench

wb = Workbench()
ident = wb.create_structure("identity")
result = wb.run_vqc(ident, "Hi", L_max=8, qec_reps=1, turbulence=0.0)
print(result.summarize())
