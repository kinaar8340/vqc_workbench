import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.simulation.lattice import LatticeUnavailable, apply_oam_backaction


def test_apply_oam_backaction_leaks_to_neighbor():
    import numpy as np

    ells = np.arange(-2, 3)
    intensity = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
    out = apply_oam_backaction(ells, intensity, ell=0, coupling_factor=0.8, ell_shift=0.1)
    assert out[ells == 0][0] < 1.0
    assert out[ells == 1][0] > 0.0
    assert pytest.approx(float(out.sum()), rel=1e-9) == 1.0


def test_couple_spiral_to_lattice():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    try:
        result = wb.couple_to_lattice(plate, kappa=0.85, steps=3, nx=8, ell=3, L_max=6, grid_size=32)
    except LatticeUnavailable:
        pytest.skip("oam_flux not importable")
    assert result.ell == 3
    assert result.steps == 3
    assert len(result.history) == 3
    assert "mean_twist" in result.history[-1]
    assert result.coupling_factor > 0
    assert 3 in result.oam_before
    assert result.history[0]["pump_active"] == 1.0
    assert result.history[0]["photon_momentum"] > 0.0


def test_kappa_sweep_two_points():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    try:
        result = wb.couple_to_lattice(
            plate,
            steps=2,
            nx=8,
            ell=1,
            L_max=4,
            grid_size=32,
            sweep_kappa=[0.80, 0.89],
        )
    except LatticeUnavailable:
        pytest.skip("oam_flux not importable")
    assert result.sweep is not None
    assert len(result.sweep) == 2
    assert result.sweep[0]["kappa"] == pytest.approx(0.80)
    assert result.sweep[1]["kappa"] == pytest.approx(0.89)
