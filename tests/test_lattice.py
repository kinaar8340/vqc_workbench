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


def test_coupling_result_summary_is_compact():
    from vqc_workbench.simulation.lattice import LatticeCouplingResult

    result = LatticeCouplingResult(
        ell=3,
        kappa=0.85,
        steps=2,
        nx=8,
        initial_mean_twist=0.73,
        final_mean_twist=0.72,
        twist_variance=0.14,
        coupling_factor=0.96,
        ell_shift=-0.0018,
        conservation_residual=1e-16,
        oam_before={3: 0.999, -1: 1e-3},
        oam_after={3: 0.997, 2: 0.002},
        history=[
            {"pump_active": 1.0, "recovery_active": 0.0, "photon_momentum": 0.8},
            {"pump_active": 0.0, "recovery_active": 1.0, "photon_momentum": 0.0},
        ],
        sweep=[
            {
                "kappa": 0.80,
                "final_mean_twist": 0.721,
                "twist_variance": 0.14,
                "coupling_factor": 0.96,
                "ell_shift": -0.0018,
                "conservation_residual": 0.0,
            }
        ],
    )
    text = result.summary()
    assert "ℓ=3" in text
    assert "κ_eff=" in text
    assert "Δℓ=" in text
    assert "OAM" in text
    assert "pump 1 step" in text
    assert "0.80" in text
    assert "history" not in text
    dumped = result.as_dict()
    assert "history" in dumped
    assert len(dumped["history"]) == 2


def test_cli_couple_default_is_summary(capsys):
    from vqc_workbench.cli import main
    from vqc_workbench.simulation.lattice import LatticeUnavailable

    try:
        rc = main(
            [
                "couple",
                "--kind",
                "spiral_phase",
                "--ell",
                "3",
                "--steps",
                "2",
                "--nx",
                "8",
                "--L-max",
                "6",
            ]
        )
    except LatticeUnavailable:
        pytest.skip("oam_flux not importable")
    assert rc == 0
    out = capsys.readouterr().out
    assert "ℓ=3" in out
    assert "κ_eff=" in out
    assert '"history"' not in out


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
