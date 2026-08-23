from pathlib import Path

import numpy as np

from vqc_workbench.api import Workbench
from vqc_workbench.core.registry import available_kinds
from vqc_workbench.utils.grid import cartesian_grid


def test_kinds_registered():
    kinds = available_kinds()
    for kind in (
        "spiral_phase",
        "binary_grating",
        "blazed_grating",
        "forked_hologram",
        "orbital_braille",
        "trajectoid",
        "flux_lattice",
        "metasurface",
        "identity",
        "custom",
    ):
        assert kind in kinds


def test_update_is_immutable():
    wb = Workbench()
    a = wb.create_grating(kind="spiral_phase", ell=2)
    b = a.update(ell=5)
    assert a.params["ell"] == 2
    assert b.params["ell"] == 5
    assert a is not b


def test_yaml_roundtrip(tmp_path: Path):
    wb = Workbench()
    src = wb.create_grating(kind="spiral_phase", ell=3)
    path = tmp_path / "spiral.yaml"
    src.to_yaml(path)
    loaded = wb.load_structure(path)
    assert loaded.kind == "spiral_phase"
    assert int(loaded.params["ell"]) == 3


def test_spiral_phase_mask_winding():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    x, y = cartesian_grid(64, 3.0)
    mask = plate.to_phase_mask((x, y), 1550.0)
    phi = np.arctan2(y, x)
    # Away from the origin, phase tracks 3φ.
    ring = (np.sqrt(x**2 + y**2) > 0.5) & (np.sqrt(x**2 + y**2) < 2.0)
    err = np.angle(mask[ring] * np.exp(-1j * 3 * phi[ring]))
    assert float(np.mean(np.abs(err))) < 0.05


def test_load_bundled_yaml():
    wb = Workbench()
    from vqc_workbench.core.config import workbench_root

    path = workbench_root() / "configs" / "structures" / "spiral_phase.yaml"
    s = wb.load_structure(path)
    assert s.kind == "spiral_phase"
    assert int(s.params["ell"]) == 3
