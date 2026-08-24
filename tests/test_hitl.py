import json
from pathlib import Path

import numpy as np
import pytest

from vqc_workbench.api import Workbench
from vqc_workbench.simulation.hitl import (
    HITLResult,
    HITLUnavailable,
    structure_phase_stack,
    write_playlist,
)


def test_hitl_result_summary_is_compact():
    result = HITLResult(
        payload=b"Hi",
        recovered=b"Hi",
        payload_match=True,
        crc_ok=True,
        channel="projector",
        profile="test-320x180",
        n_proxy_frames=40,
        slm_frames=8,
        playlist_dir="/tmp/hitl/playlist",
        device="generic_512",
        bit_errors=0,
        bits_compared=16,
    )
    text = result.summary()
    assert "MATCH" in text
    assert "payload='Hi'" in text
    assert "playlist  8 frames" in text
    assert "history" not in text
    dumped = result.as_dict()
    assert dumped["payload_match"] is True
    assert dumped["crc_ok"] is True


def test_structure_playlist_varies_for_orbital_braille():
    wb = Workbench()
    braille = wb.create_orbital_braille(n_orbs=4)
    stack, cfg = structure_phase_stack(braille, n_frames=3, device="generic_512", grid_size=32)
    assert stack.shape[0] == 3
    assert cfg.name == "generic_512"
    assert not np.allclose(stack[0], stack[-1])


def test_write_playlist_layout(tmp_path: Path):
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=1)
    stack, cfg = structure_phase_stack(plate, n_frames=2, device="generic_512", grid_size=32)
    dest = write_playlist(stack, tmp_path / "playlist", cfg=cfg, extra={"playlist_kind": "structure"})
    assert (dest / "phase_stack.npy").is_file()
    assert (dest / "manifest.json").is_file()
    assert (dest / "frames" / "phase_0000.raw").is_file()
    meta = json.loads((dest / "manifest.json").read_text())
    assert meta["n_phase_frames"] == 2
    assert meta["playlist_kind"] == "structure"
    loaded = np.load(dest / "phase_stack.npy")
    assert loaded.shape == stack.shape


def test_hitl_clean_loopback_matches_payload(tmp_path: Path):
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    try:
        result = wb.hitl(
            "Hi",
            plate,
            channel="clean",
            n_frames=2,
            device="generic_512",
            grid_size=32,
            out=tmp_path / "hitl",
        )
    except HITLUnavailable:
        pytest.skip("vqc_demo not importable")
    assert result.crc_ok
    assert result.payload_match
    assert result.recovered == b"Hi"
    assert result.channel == "clean"
    assert result.slm_frames == 2
    assert result.playlist_dir is not None
    assert Path(result.playlist_dir).joinpath("phase_stack.npy").is_file()
    assert result.bit_errors == 0
    assert result.proxy_dir is not None
    assert Path(result.proxy_dir).is_dir()
    assert any(Path(result.proxy_dir).glob("frame_*.png"))


def test_hitl_camera_roundtrip_from_written_frames(tmp_path: Path):
    wb = Workbench()
    try:
        tx = wb.hitl("Hi", channel="clean", n_frames=2, out=tmp_path / "cam", grid_size=32)
    except HITLUnavailable:
        pytest.skip("vqc_demo not importable")
    assert tx.payload_match
    frames = Path(tx.proxy_dir)
    roundtrip = wb.hitl("Hi", capture=frames, n_frames=2, out=None)
    assert roundtrip.channel == "capture"
    assert roundtrip.payload_match
    assert roundtrip.recovered == b"Hi"


def test_cli_hitl_default_is_summary(capsys, tmp_path: Path):
    from vqc_workbench.cli import main

    try:
        rc = main(
            [
                "hitl",
                "--payload",
                "Hi",
                "--kind",
                "spiral_phase",
                "--ell",
                "1",
                "--channel",
                "clean",
                "--frames",
                "2",
                "--out",
                str(tmp_path / "cli-hitl"),
            ]
        )
    except HITLUnavailable:
        pytest.skip("vqc_demo not importable")
    assert rc == 0
    out = capsys.readouterr().out
    assert "MATCH" in out
    assert "HITL" in out
    assert '"report"' not in out
