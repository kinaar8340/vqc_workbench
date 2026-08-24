import numpy as np
import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.structures.trajectoid import TrajectoidLiveUnavailable
from vqc_workbench.utils.grid import cartesian_grid


def test_analytic_trajectoid_is_still_the_default():
    wb = Workbench()
    shell = wb.create_trajectoid(n_trenches=8, winding=2)
    assert shell.params.get("live") is False
    spec = shell.to_geometry_dict()
    assert spec["live_shell"] is False
    assert spec["engine"] == "analytic"
    x, y = cartesian_grid(32, 2.0)
    mask = shell.to_phase_mask((x, y), 1550.0)
    assert np.allclose(np.abs(mask), 1.0, atol=1e-9)


def test_live_shell_replaces_analytic_trench():
    wb = Workbench()
    analytic = wb.create_trajectoid(n_trenches=8, winding=2, payload_hash="vqc")
    try:
        live = wb.create_trajectoid(n_trenches=8, winding=2, payload_hash="vqc", live=True)
        x, y = cartesian_grid(48, 2.0)
        a = analytic.to_phase_mask((x, y), 1550.0)
        b = live.to_phase_mask((x, y), 1550.0)
    except TrajectoidLiveUnavailable:
        pytest.skip("flux_trajectoid not importable")
    assert np.allclose(np.abs(b), 1.0, atol=1e-6)
    assert not np.allclose(np.angle(a), np.angle(b), atol=0.05)
    spec = live.to_geometry_dict()
    assert spec["live_shell"] is True
    assert spec["engine"] == "flux_trajectoid.generate_shell"
    assert "shell" in spec
    assert spec["shell"]["fourier_fingerprint"] is not None
    geo = live.live_shell()
    assert geo is not None
    assert live.live_shell() is geo  # cached


def test_live_forecast_has_no_closed_form_charge():
    wb = Workbench()
    try:
        live = wb.create_trajectoid(n_trenches=8, winding=2, live=True)
        live.live_shell()
    except TrajectoidLiveUnavailable:
        pytest.skip("flux_trajectoid not importable")
    fc = wb.forecast_charge(live)
    assert fc.expected_ell is None
    assert "generate_shell" in fc.formula
    analytic = wb.create_trajectoid(n_trenches=8, winding=2)
    assert wb.forecast_charge(analytic).expected_ell == -6


def test_cli_simulate_live(capsys):
    from vqc_workbench.cli import main

    try:
        rc = main(
            [
                "simulate",
                "--kind",
                "trajectoid",
                "--n-trenches",
                "8",
                "--winding",
                "2",
                "--live",
                "--payload-hash",
                "vqc",
                "--L-max",
                "6",
            ]
        )
    except TrajectoidLiveUnavailable:
        pytest.skip("flux_trajectoid not importable")
    assert rc == 0
    out = capsys.readouterr().out
    assert "generate_shell" in out
    assert "expected_ell=n/a" in out
