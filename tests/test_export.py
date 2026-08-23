import json
from pathlib import Path

import numpy as np
import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.export.slm import SLM_PRESETS, phase_to_levels


def test_export_slm_writes_npy(tmp_path: Path):
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    path = wb.export_slm(plate, tmp_path / "phase.npy", device="generic_512")
    assert path.is_file()
    mask = np.load(path)
    assert mask.ndim == 2
    assert np.iscomplexobj(mask)
    levels_path = path.with_name("phase_levels.npy")
    assert levels_path.is_file()


def test_phase_to_levels_range():
    phase = np.exp(1j * np.linspace(0, 2 * np.pi, 16, endpoint=False))
    levels = phase_to_levels(phase, bit_depth=8)
    assert levels.dtype == np.uint16
    assert int(levels.min()) >= 0
    assert int(levels.max()) <= 255


def test_presets_include_holoeye():
    assert "holoeye_pluto_2" in SLM_PRESETS
    assert "generic_512" in SLM_PRESETS
    assert "meadowlark_512" in SLM_PRESETS
    assert "thorlabs_1080p" in SLM_PRESETS


@pytest.mark.parametrize("device", sorted(SLM_PRESETS))
@pytest.mark.parametrize("kind", ["spiral_phase", "orbital_braille", "binary_grating"])
def test_slm_export_valid_for_device_presets(tmp_path: Path, device: str, kind: str):
    wb = Workbench()
    if kind == "spiral_phase":
        structure = wb.create_grating(kind="spiral_phase", ell=1)
    elif kind == "binary_grating":
        structure = wb.create_grating(kind="binary_grating", period=0.4)
    else:
        structure = wb.create_orbital_braille(n_orbs=4)
    out = tmp_path / f"{kind}_{device}.npy"
    path = wb.export_slm(structure, out, device=device)
    assert path.is_file()
    mask = np.load(path)
    assert mask.ndim == 2
    assert np.iscomplexobj(mask)
    assert np.isfinite(mask).all()
    levels = np.load(path.with_name(path.stem + "_levels.npy"))
    bit_depth = int(SLM_PRESETS[device]["bit_depth"])
    assert int(levels.min()) >= 0
    assert int(levels.max()) <= (1 << bit_depth) - 1
    manifest = json.loads(path.with_name(path.stem + "_manifest.json").read_text())
    assert manifest["device"]["name"] == device
    assert "structure" in manifest
