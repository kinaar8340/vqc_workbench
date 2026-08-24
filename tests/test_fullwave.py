import os

import numpy as np
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
        import grcwa  # noqa: F401
    except ImportError:
        try:
            import nannos  # noqa: F401
        except ImportError:
            with pytest.raises(FullWaveUnavailable, match="RCWA|grcwa|nannos"):
                wb.simulate_fullwave(g, backend="rcwa", L_max=4, grid_size=32)
            return
    result = wb.simulate_fullwave(g, backend="rcwa", L_max=4, grid_size=32, nG=9, use_cache=False)
    assert result.backend == "rcwa"
    assert result.extras.get("layout") == "layer_stack"
    assert "scalar projector" not in (result.extras.get("note") or "")


def test_rcwa_binary_layer_stack_conserves_power():
    pytest.importorskip("grcwa")
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    result = wb.simulate_fullwave(
        g, backend="rcwa", L_max=4, grid_size=32, extent=3.5, nG=15, use_cache=False
    )
    assert result.backend == "rcwa"
    assert result.extras["engine"] == "grcwa"
    assert result.extras["layout"] == "layer_stack"
    assert abs(result.extras["R_total"] + result.extras["T_total"] - 1.0) < 0.05
    assert result.ell.shape == result.coefficients.shape
    assert result.T is not None


def test_rcwa_stack_builder_uses_grating_period():
    from vqc_workbench.simulation.rcwa import structure_to_stack

    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    stack = structure_to_stack(g, grid_size=16, nG=9)
    assert stack.period_x == pytest.approx(0.4)
    assert stack.layers[1].patterned
    assert np.asarray(stack.layers[1].epsilon).shape == (16, 16)
    assert stack.extras["unit_cell"] == "period"


def test_nannos_layer_stack_optional():
    pytest.importorskip("nannos")
    wb = Workbench()
    g = wb.create_grating(kind="binary_grating", period=0.4, duty=0.5)
    result = wb.simulate_fullwave(
        g,
        backend="rcwa",
        engine="nannos",
        L_max=4,
        grid_size=32,
        extent=3.5,
        nG=15,
        use_cache=False,
    )
    assert result.extras["engine"] == "nannos"
    assert abs(result.extras["R_total"] + result.extras["T_total"] - 1.0) < 0.05


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


def test_fullwave_cache_hits(monkeypatch):
    monkeypatch.setenv("VQC_FULLWAVE_CACHE", "0")
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    a = wb.simulate_fullwave(g, backend="scalar", L_max=4, grid_size=48, z=0.0)
    b = wb.simulate_fullwave(g, backend="scalar", L_max=4, grid_size=48, z=0.0)
    assert a.cached is False
    assert b.cached is True
    assert a.dominant_ell() == b.dominant_ell()


def test_phase_to_slab_index_encodes_full_helix():
    from vqc_workbench.simulation.fullwave import phase_to_slab_index
    from vqc_workbench.utils.grid import cartesian_grid, polar_from_cartesian

    x, y = cartesian_grid(48, 2.0)
    _, phi = polar_from_cartesian(x, y)
    mask = np.exp(1j * phi)
    n_map, meta = phase_to_slab_index(mask, thickness=1.0, wavelength=1.0, n_lo=1.2)
    assert meta["encoding"] == "full_2pi"
    assert meta["phase_depth_rad"] == pytest.approx(2.0 * np.pi)
    assert float(n_map.min()) >= 1.2 - 1e-9
    assert float(n_map.max()) <= meta["n_hi"] + 1e-9
    # Both signs of the helix survive (not collapsed onto n=1).
    assert float(n_map.max() - n_map.min()) == pytest.approx(meta["n_hi"] - 1.2, abs=0.05)


def test_fullwave_disk_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("VQC_FULLWAVE_CACHE", str(tmp_path))
    from vqc_workbench.simulation.fullwave import FullWaveCache, FullWaveEngine

    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    eng = FullWaveEngine(cache=FullWaveCache(disk_dir=tmp_path), modal=wb.modal)
    a = eng.run(g, backend="scalar", L_max=4, grid_size=32, z=0.0)
    files = list(tmp_path.glob("*.npz"))
    assert len(files) == 1
    eng2 = FullWaveEngine(cache=FullWaveCache(disk_dir=tmp_path), modal=wb.modal)
    b = eng2.run(g, backend="scalar", L_max=4, grid_size=32, z=0.0)
    assert a.cached is False
    assert b.cached is True
    assert b.dominant_ell() == a.dominant_ell()
    assert np.allclose(a.intensity, b.intensity)


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
def test_meep_thin_plate_uses_full_2pi_encoding():
    pytest.importorskip("meep")
    wb = Workbench()
    g = wb.create_grating(kind="spiral_phase", ell=1)
    result = wb.simulate_fullwave(
        g,
        backend="meep",
        L_max=4,
        grid_size=32,
        extent=3.5,
        resolution=16,
        layout="thin_plate_3d",
        pml=1.0,
        sz=6.0,
        until=40,
        w0=1.0,
        use_cache=False,
    )
    assert result.extras.get("encoding") == "full_2pi"
    assert result.extras.get("phase_depth_rad") == pytest.approx(2.0 * np.pi, rel=0.05)
    # Charge recovery at affordable res is still a negative (ℓ ≠ +1). Encoding
    # is the 2π map; source-imprint remains the validated FDTD charge path.


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
