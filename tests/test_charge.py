from vqc_workbench.api import Workbench


def test_spiral_forecast_matches_peak():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    fc = wb.forecast_charge(plate)
    modes = wb.simulate_modes(plate, L_max=8, grid_size=64)
    assert fc.expected_ell == 3
    assert fc.mode_shifter is True
    assert modes.dominant_ell() == 3


def test_trajectoid_winding_minus_trenches():
    wb = Workbench()
    shell = wb.create_trajectoid(n_trenches=8, winding=2)
    fc = wb.forecast_charge(shell)
    assert fc.expected_ell == 2 - 8
    assert fc.mode_shifter is True
    modes = wb.simulate_modes(shell, L_max=8, grid_size=96)
    assert modes.dominant_ell() == fc.expected_ell
    assert float(modes.intensity[modes.ell == fc.expected_ell][0]) > 0.8


def test_identity_is_not_a_shifter():
    wb = Workbench()
    ident = wb.create_structure("identity")
    fc = wb.forecast_charge(ident)
    assert fc.expected_ell == 0
    assert fc.mode_shifter is False


def test_live_turbulence_lowers_spiral_purity():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    clean = wb.simulate_modes(plate, L_max=6, grid_size=64, turbulence=0.0)
    dirty = wb.simulate_modes(plate, L_max=6, grid_size=64, turbulence=1.5, seed=0)
    p_clean = float((clean.intensity**2).sum())
    p_dirty = float((dirty.intensity**2).sum())
    assert p_clean > p_dirty
