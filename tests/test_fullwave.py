import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.simulation.fullwave import FullWaveUnavailable


def test_meep_fails_loudly_when_missing():
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4)
    try:
        import meep  # noqa: F401
    except ImportError:
        with pytest.raises(FullWaveUnavailable, match="Meep"):
            wb.simulate_fullwave(g, backend="meep", L_max=4, grid_size=32)
    else:
        pytest.skip("meep is installed; loud-fail path not exercised")


def test_rcwa_fails_loudly_when_missing():
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating")
    try:
        result = wb.simulate_fullwave(g, backend="rcwa", L_max=4, grid_size=32)
    except FullWaveUnavailable as exc:
        assert "RCWA" in str(exc) or "grcwa" in str(exc).lower()
        return
    assert result.backend == "rcwa"


def test_scalar_vs_modal_binary_grating():
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    cmp = wb.compare_backends(g, backends=("modal", "scalar"), L_max=6, grid_size=64, z=0.0)
    assert cmp["cosine"] > 0.98
    assert cmp["dominant_match"]


def test_scalar_vs_modal_spiral():
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=3)
    cmp = wb.compare_backends(g, backends=("modal", "scalar"), L_max=8, grid_size=80, z=0.0)
    assert cmp["dominant_ell_a"] == 3
    assert cmp["dominant_ell_b"] == 3
    assert cmp["cosine"] > 0.98


def test_fullwave_cache_hits():
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    a = wb.simulate_fullwave(g, backend="scalar", L_max=4, grid_size=48, z=0.0)
    b = wb.simulate_fullwave(g, backend="scalar", L_max=4, grid_size=48, z=0.0)
    assert a.cached is False
    assert b.cached is True
    assert a.dominant_ell() == b.dominant_ell()
