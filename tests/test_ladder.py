from pathlib import Path

import numpy as np
import yaml

from vqc_workbench.ladder.engine import LadderEngine
from vqc_workbench.ladder.frames import axial_for_stage, st_for_stage
from vqc_workbench.ladder.model import (
    SELECT_GLOW,
    LadderDocument,
    beam_evolution_ladder,
    save_ladder,
)
from vqc_workbench.ladder.render import render_ladder


def test_glow_is_pure_green():
    assert SELECT_GLOW == "#00FF00"


def test_default_ladder_hierarchy():
    doc = beam_evolution_ladder()
    assert len(doc.rungs) == 4
    titles = [r.title for r in doc.rungs]
    assert titles == ["INITIAL", "SLM STAGE", "HELICAL FORMATION", "MULTI-LAYER / DETECTION"]
    for rung in doc.rungs:
        assert rung.axial is not None
        assert rung.spatiotemporal is not None
        assert rung.axial.view == "axial"
        assert rung.spatiotemporal.view == "spatiotemporal"
        assert rung.equipment, "equipment row required under every logic rung"
        assert rung.contacts
    # lab mapping (tags live on the rung, not beside some other rung)
    e1 = [d.tag for d in doc.rungs[0].equipment]
    assert "[LASER_532]" in e1 and "[BE_01]" in e1 and "[L1]" in e1 and "[IRIS_01]" in e1
    e2 = [d.tag for d in doc.rungs[1].equipment]
    assert "[SLM_01]" in e2 and "[HWP_01]" in e2
    e3 = [d.tag for d in doc.rungs[2].equipment]
    assert "[DIFF_01]" in e3 and "[LCP_01]" in e3
    e4 = [d.tag for d in doc.rungs[3].equipment]
    assert "[CAM1]" in e4 and "[CAM2]" in e4 and "[FIBER_01]" in e4 and "[NODE_AX]" in e4
    ids = doc.all_node_ids()
    assert len(ids) == len(set(ids))


def test_prototype_frame_pairing():
    doc = beam_evolution_ladder()
    assert doc.rungs[0].axial.frame_ids == [1, 2, 3]
    assert doc.rungs[0].spatiotemporal.frame_ids == [4, 5]
    assert doc.rungs[1].axial.frame_ids == [6, 7, 8]
    assert doc.rungs[1].spatiotemporal.frame_ids == [9, 10]
    assert doc.rungs[2].axial.frame_ids == [11, 12]
    assert doc.rungs[2].spatiotemporal.frame_ids == [13]
    assert doc.rungs[3].axial.frame_ids == [14, 15]
    assert doc.rungs[3].spatiotemporal.frame_ids == [16]
    assert doc.n_pulse_frames == 16


def test_yaml_roundtrip(tmp_path: Path):
    doc = beam_evolution_ladder()
    doc.select("rung2.slm")
    path = tmp_path / "ladder.yaml"
    save_ladder(doc, path)
    raw = yaml.safe_load(path.read_text())
    again = LadderDocument.from_dict(raw)
    assert again.selected_node_id == "rung2.slm"
    assert again.rungs[1].workbench["kind"] == "spiral_phase"
    assert again.wavelength_nm == 532.0


def test_selection_glow_persists_until_trigger_or_reselect():
    doc = beam_evolution_ladder()
    doc.select("rung1.pulse_in")
    assert doc.selected_node_id == "rung1.pulse_in"
    doc.select("rung2.slm")
    assert doc.selected_node_id == "rung2.slm"
    closed_before = next(c.closed for c in doc.rungs[1].contacts if c.id == "slm_en")
    doc.trigger("rung2.slm_en")
    # triggering a different node does not clear the SLM_01 glow
    assert doc.selected_node_id == "rung2.slm"
    doc.trigger("rung2.slm")
    assert doc.selected_node_id is None
    # contact toggle still works
    slm_en = next(c for c in doc.rungs[1].contacts if c.id == "slm_en")
    assert slm_en.closed != closed_before


def test_unknown_node_rejected():
    doc = beam_evolution_ladder()
    try:
        doc.select("nope.missing")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_add_delete_reorder():
    doc = beam_evolution_ladder()
    n = len(doc.rungs)
    added = doc.add_rung()
    assert len(doc.rungs) == n + 1
    assert added.axial is not None and added.equipment
    doc.move_rung(added.id, -1)
    doc.delete_rung(added.id)
    assert len(doc.rungs) == n
    assert [r.number for r in doc.rungs] == [1, 2, 3, 4]


def test_frames_are_monitor_rgb():
    ax = axial_for_stage("initial", n=32)
    st = st_for_stage("slm", n=32, ell=1)
    assert ax.shape == (32, 32, 3) and ax.dtype == np.uint8
    assert st.ndim == 3 and st.shape[2] == 3 and st.dtype == np.uint8
    helical = axial_for_stage("helical", n=32, layers=3)
    detect = st_for_stage("detect", n=32, layers=4)
    assert helical.shape[-1] == 3 and detect.shape[-1] == 3


def test_engine_binds_workbench_and_spectrum():
    doc = beam_evolution_ladder()
    doc.grid_size = 32
    doc.L_max = 6
    doc.select("rung2.axial")
    rt = LadderEngine(grid_size=32).bind(doc)
    assert set(rt.rungs) == {r.id for r in doc.rungs}
    slm = rt.rungs["rung2"]
    assert slm.kind == "spiral_phase"
    assert slm.axial.shape[2] == 3
    assert slm.spatiotemporal.shape[2] == 3
    assert slm.modes is not None
    spec = rt.spectrum
    assert spec is not None
    assert spec.node_id == "rung2.axial"
    assert spec.axis == "ell"
    assert spec.peak_label.startswith("ell=")
    # laser node is a wavelength trace
    doc.select("rung1.laser")
    spec_l = LadderEngine(grid_size=32).bind(doc).spectrum
    assert spec_l.axis == "wavelength_nm"
    assert spec_l.peak_label.startswith("wl=")


def test_scan_tick_advances_cycle_and_frame():
    doc = beam_evolution_ladder()
    doc.scan_active = True
    doc.cycle = 0
    doc.frame_index = 0
    eng = LadderEngine(grid_size=32)
    eng.tick(doc)
    assert doc.cycle == 1
    assert doc.frame_index == 1
    doc.scan_active = False
    eng.tick(doc)
    assert doc.cycle == 1


def test_static_hmi_render(tmp_path: Path):
    doc = beam_evolution_ladder()
    doc.grid_size = 32
    doc.cycle = 42
    rt = LadderEngine(grid_size=32).bind(doc)
    path = tmp_path / "ladder_hmi.png"
    fig = render_ladder(doc, rt, path, dpi=60)
    assert path.is_file()
    assert path.stat().st_size > 8_000
    fig.clear()


def test_spectrum_axis_laser_vs_structure():
    from vqc_workbench.ladder.engine import auto_spectrum_axis

    doc = beam_evolution_ladder()
    doc.grid_size = 32
    assert auto_spectrum_axis(doc, "rung1.laser") == "wavelength_nm"
    assert auto_spectrum_axis(doc, "rung1.trig_532") == "wavelength_nm"
    assert auto_spectrum_axis(doc, "rung2.slm") == "ell"
    assert auto_spectrum_axis(doc, "rung2.axial") == "ell"
    eng = LadderEngine(grid_size=32)
    doc.select("rung2.slm")
    spec = eng.bind(doc).spectrum
    assert spec.axis == "ell"
    doc.spectrum_axis = "wavelength_nm"
    spec_w = eng.bind(doc).spectrum
    assert spec_w.axis == "wavelength_nm"
    assert spec_w.peak_label.startswith("wl=")
    doc.spectrum_axis = None
    doc.select("rung1.laser")
    spec_l = eng.bind(doc).spectrum
    assert spec_l.axis == "wavelength_nm"


def test_presets_and_prototype_sequence():
    from vqc_workbench.ladder.model import list_ladder_presets, load_ladder_preset

    stems = {p.stem for p in list_ladder_presets()}
    assert "beam_evolution" in stems
    assert "slm_playlist" in stems
    proto = load_ladder_preset("beam_evolution")
    assert len(proto.rungs) == 4
    assert proto.selected_node_id == "rung1.pulse_in"
    slm = load_ladder_preset("slm_playlist")
    assert slm.selected_node_id == "rung2.slm"
    assert slm.rungs[1].equipment[0].tag == "[SLM_01]"


def test_prototype_physics_frames():
    from vqc_workbench.ladder.prototype import fr1_3_axial, fr6_8_axial, fr9_10_st, fr11_12_axial

    ax = fr1_3_axial(n=48)
    assert ax.shape == (48, 48, 3) and ax.dtype == np.uint8
    slm = fr6_8_axial(n=48)
    assert slm.shape == (48, 48, 3)
    st = fr9_10_st(ny=40, nx=64)
    assert st.shape == (40, 64, 3)
    nest = fr11_12_axial(n=48)
    assert nest.shape[-1] == 3


def test_monitor_assets_and_hitl_override():
    from vqc_workbench.ladder.frames import load_monitor_asset, monitor_image

    rgb = load_monitor_asset("slm", "axial")
    assert rgb is not None and rgb.ndim == 3 and rgb.shape[2] == 3
    st = load_monitor_asset("initial", "st")
    assert st is not None and st.shape[1] >= st.shape[0]
    fake = np.full((10, 12, 3), 7, dtype=np.uint8)
    out = monitor_image("initial", "axial", n=16, override=fake)
    assert out.shape == (10, 12, 3) and int(out[0, 0, 0]) == 7
    doc = beam_evolution_ladder()
    doc.grid_size = 32
    eng = LadderEngine(grid_size=32)
    eng.set_hitl_frame("rung4", axial=fake)
    rt = eng.bind(doc)
    assert rt.rungs["rung4"].axial.shape == (10, 12, 3)


def test_instruction_list_export():
    from vqc_workbench.ladder.export import export_instruction_list

    doc = beam_evolution_ladder()
    text = export_instruction_list(doc)
    assert "NETWORK 01  INITIAL" in text
    assert "XIC   PULSE_IN" in text
    assert "ONS   TRIG_532" in text
    assert "[LASER_532] -> [BE_01]" in text
    assert "NETWORK 04" in text
    assert "OTE   RUNG2_BEAM" in text
