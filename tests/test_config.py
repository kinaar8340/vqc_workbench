from vqc_workbench.adapters import probe_ecosystem
from vqc_workbench.api import Workbench
from vqc_workbench.core.config import load_config, workbench_root


def test_default_config_loads():
    root = workbench_root()
    assert (root / "configs" / "default.yaml").is_file()
    cfg = load_config()
    assert cfg.wavelength_nm == 1550.0
    assert cfg.L_max >= 2


def test_material_library():
    wb = Workbench()
    sil = wb.materials.get("fused_silica")
    n = sil.index(1550.0)
    assert n.real > 1.3
    assert "silicon" in wb.materials.names()


def test_ecosystem_probe():
    status = probe_ecosystem()
    d = status.as_dict()
    assert "flux_hopf_lib" in d
    assert "meep" in d
