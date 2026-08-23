import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.simulation.metrics import oam_purity


@pytest.mark.parametrize("ell", [-2, 1, 2, 3])
def test_spiral_plate_seeds_target_ell(ell):
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=ell)
    modes = wb.simulate_modes(plate, L_max=8, grid_size=96)
    assert modes.dominant_ell() == ell
    i_ell = float(modes.intensity[modes.ell == ell][0])
    assert i_ell > 0.35


def test_forked_hologram_carries_target_ell():
    """A forked hologram is spiral × linear carrier; demodulate to recover ℓ."""
    import numpy as np

    from vqc_workbench.simulation.lg import gaussian_beam, project_oam_spectrum

    wb = Workbench()
    ell = 2
    period = 0.8
    fork = wb.create_grating(kind="forked_hologram", ell=ell, period=period)
    modes = wb.simulate_modes(fork, L_max=8, grid_size=96)
    carrier = 2.0 * np.pi * modes.x / period
    demod = modes.phase_mask * np.exp(-1j * carrier)
    field = gaussian_beam(modes.x, modes.y, w0=wb.config.w0) * demod
    weights = project_oam_spectrum(field, modes.x, modes.y, L_max=8, w0=wb.config.w0)
    dominant = max(weights, key=lambda k: abs(weights[k]))
    assert dominant == ell


def test_orbital_braille_is_multimode():
    wb = Workbench()
    braille = wb.create_orbital_braille(n_orbs=4)
    modes = wb.simulate_modes(braille, L_max=8, grid_size=80)
    n_hot = int((modes.intensity > 0.05).sum())
    assert n_hot >= 2
    purity = float((modes.intensity**2).sum())
    assert purity < 0.95


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
