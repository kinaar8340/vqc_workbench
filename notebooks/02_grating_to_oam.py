"""Forked hologram and binary grating → OAM spectra."""

from vqc_workbench import Workbench

wb = Workbench()
for kind, kwargs in (
    ("spiral_phase", {"ell": 3}),
    ("forked_hologram", {"ell": 2, "period": 0.35}),
    ("binary_grating", {"period": 0.4}),
):
    s = wb.create_grating(kind=kind, **kwargs)
    m = wb.simulate_modes(s, L_max=8)
    print(f"{kind:16s}  dominant ℓ={m.dominant_ell():+d}")
