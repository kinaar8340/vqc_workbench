from pathlib import Path

import numpy as np

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
