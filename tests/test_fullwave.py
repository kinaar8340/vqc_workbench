import os

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


def test_meep_opt_in_gate(monkeypatch):
    pytest.importorskip("meep")
    monkeypatch.delenv("VQC_MEEP_RUN", raising=False)
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    with pytest.raises(FullWaveUnavailable, match="VQC_MEEP_RUN"):
        wb.simulate_fullwave(g, backend="meep", L_max=4, grid_size=32)


_MEEP = os.environ.get("VQC_MEEP_RUN", "").lower() in {"1", "true", "yes"}


@pytest.mark.skipif(not _MEEP, reason="set VQC_MEEP_RUN=1 to run the Meep FDTD agreement check")
def test_meep_spiral_agrees_with_modal():
    pytest.importorskip("meep")
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    cmp = wb.compare_backends(
        g, backends=("modal", "meep"), L_max=4, grid_size=24, extent=3.0, resolution=10
    )
    assert cmp["backend_b"] == "meep"
    assert cmp["dominant_ell_b"] == 1


@pytest.mark.skipif(not _MEEP, reason="set VQC_MEEP_RUN=1 to run the Meep FDTD agreement check")
def test_meep_metasurface_ell1_agrees_with_modal():
    pytest.importorskip("meep")
    wb = Workbench()
    m = wb.create_metasurface(ell_target=1)
    cmp = wb.compare_backends(
        m, backends=("modal", "meep"), L_max=4, grid_size=24, extent=3.0, resolution=10
    )
    assert cmp["dominant_ell_a"] == 1
    assert cmp["dominant_ell_b"] == 1
    assert cmp["cosine"] > 0.9


@pytest.mark.skipif(not _MEEP, reason="set VQC_MEEP_RUN=1 to run the Meep FDTD agreement check")
def test_meep_binary_grating_matches_modal_shape():
    pytest.importorskip("meep")
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    cmp = wb.compare_backends(
        g, backends=("modal", "meep"), L_max=4, grid_size=24, extent=3.0, resolution=10
    )
    # 1-D gratings are not topological-charge plates; require spectral agreement.
    assert cmp["cosine"] > 0.75


@pytest.mark.skipif(not _MEEP, reason="set VQC_MEEP_RUN=1 to run the Meep FDTD agreement check")
def test_meep_forked_hologram_matches_modal_shape():
    pytest.importorskip("meep")
    wb = Workbench()
    g = wb.create_grating(kind="forked_hologram", ell=1, period=0.35)
    cmp = wb.compare_backends(
        g, backends=("modal", "meep"), L_max=4, grid_size=24, extent=3.0, resolution=10
    )
    # Linear carrier spreads near-field OAM; Meep should still track the modal projector.
    assert cmp["dominant_match"]
    assert cmp["cosine"] > 0.65


def test_compare_many_modal_scalar():
    from vqc_workbench.simulation.compare import compare_many

    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=2)
    r1 = wb.simulate_fullwave(g, backend="modal", L_max=6, grid_size=48)
    r2 = wb.simulate_fullwave(g, backend="scalar", L_max=6, grid_size=48, z=0.0)
    many = compare_many([r1, r2])
    assert many["dominant_ell"]["modal"] == 2
    assert many["dominant_ell"]["scalar"] == 2
    assert many["pairwise"][0]["cosine"] > 0.98
