from vqc_workbench.api import Workbench
from vqc_workbench.simulation.metrics import oam_purity


def test_spiral_plate_seeds_target_ell():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    modes = wb.simulate_modes(plate, L_max=8, grid_size=96)
    assert modes.dominant_ell() == 3
    i3 = float(modes.intensity[modes.ell == 3][0])
    assert i3 > 0.35


def test_identity_is_mostly_ell0():
    wb = Workbench()
    ident = wb.create_structure("identity")
    modes = wb.simulate_modes(ident, L_max=6, grid_size=64)
    assert modes.dominant_ell() == 0
    assert float(modes.intensity[modes.ell == 0][0]) > 0.8


def test_oam_purity_bounds():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    modes = wb.simulate_modes(plate, L_max=6, grid_size=64)
    p = oam_purity(modes.coefficients)
    assert 0.0 < p <= 1.0 + 1e-9


def test_propagate_shape():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=2)
    modes = wb.simulate_modes(plate, L_max=4, grid_size=48)
    prop = wb.modal.propagate(modes, n_z=10, turbulence=0.0)
    assert prop.intensity.shape == (10, modes.ell.size)
    assert prop.coefficients_z.shape == (10, modes.ell.size)
