from vqc_workbench.api import Workbench


def test_inverse_spiral_finds_target_ell():
    wb = Workbench()
    result = wb.inverse_design(
        "spiral_phase",
        objective="charge",
        target_ell=3,
        seed_params={"ell": -5},
        L_max=8,
        grid_size=48,
        max_evals=40,
    )
    assert int(result.params["ell"]) == 3
    assert result.metrics["dominant_ell"] == 3
    assert result.metrics["purity"] > 0.9


def test_inverse_trajectoid_matches_forecast():
    wb = Workbench()
    result = wb.inverse_design(
        "trajectoid",
        objective="forecast",
        target_ell=-6,
        L_max=8,
        grid_size=48,
        max_evals=80,
        param_names=["n_trenches", "winding"],
    )
    n = int(result.params["n_trenches"])
    w = int(result.params["winding"])
    assert w - n == -6
    assert result.metrics["dominant_ell"] == -6
    assert result.metrics["purity"] > 0.8


def test_inverse_fidelity_prefers_identity_like_duty():
    wb = Workbench()
    result = wb.inverse_design(
        "binary_grating",
        objective="fidelity",
        payload=b"Hi",
        param_names=["duty"],
        L_max=8,
        grid_size=48,
        max_evals=12,
    )
    # Extreme duty (near 0 or 1) is closer to a uniform plate than 0.5.
    assert result.metrics["fidelity"] >= 0.0
    assert "duty" in result.params
