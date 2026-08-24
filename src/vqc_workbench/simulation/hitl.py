"""Hardware-in-the-loop: SLM playlist → vqc_demo projector proxy.

The coherent artifact is a phase-only playlist (workbench structure mask
and/or vqc_demo nested-LG hologram). The VPL-HW20A path is an intensity
RGB proxy that validates framing, ring sampling, and QEC — not free-space
OAM. Workbench imports vqc_demo; vqc_demo must never import the workbench.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import Structure
from vqc_workbench.export.slm import SLMConfig, phase_to_levels
from vqc_workbench.utils.grid import cartesian_grid
from vqc_workbench.utils.io import ensure_dir


DISCLAIMER = (
    "SLM playlist is coherent phase for a laser + phase-only panel. "
    "The projector proxy is intensity RGB (VPL-HW20A class) and is not a "
    "free-space OAM BER."
)


class HITLUnavailable(RuntimeError):
    pass


def _load_vqc_demo():
    try:
        from vqc_workbench.adapters import import_vqc_demo

        return import_vqc_demo()
    except ImportError as exc:
        raise HITLUnavailable(
            "vqc_demo is not importable. pip install -e ../vqc_demo "
            "or keep the checkout at ~/Projects/vqc_demo."
        ) from exc


@dataclass
class HITLResult:
    payload: bytes
    recovered: bytes
    payload_match: bool
    crc_ok: bool
    channel: str
    profile: str
    n_proxy_frames: int
    slm_frames: int
    playlist_dir: str | None
    device: str
    bit_errors: int
    bits_compared: int
    disclaimer: str = DISCLAIMER
    report: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "payload": self.payload.decode("utf-8", errors="replace"),
            "recovered": self.recovered.decode("utf-8", errors="replace"),
            "payload_match": self.payload_match,
            "crc_ok": self.crc_ok,
            "channel": self.channel,
            "profile": self.profile,
            "n_proxy_frames": self.n_proxy_frames,
            "slm_frames": self.slm_frames,
            "playlist_dir": self.playlist_dir,
            "device": self.device,
            "bit_errors": self.bit_errors,
            "bits_compared": self.bits_compared,
            "disclaimer": self.disclaimer,
            "report": self.report,
        }

    def summary(self) -> str:
        status = "MATCH" if self.payload_match and self.crc_ok else "MISMATCH"
        rec = self.recovered.decode("utf-8", errors="replace")
        pay = self.payload.decode("utf-8", errors="replace")
        lines = [
            f"HITL  payload={pay!r}  channel={self.channel}  profile={self.profile}",
            (
                f"{status}  crc_ok={self.crc_ok}  BER={self.bit_errors}/{self.bits_compared}"
                f"  recovered={rec!r}"
            ),
            (
                f"playlist  {self.slm_frames} frames  {self.device}"
                + (f"  → {self.playlist_dir}" if self.playlist_dir else "")
            ),
            f"proxy    {self.n_proxy_frames} intensity frames",
            self.disclaimer,
        ]
        return "\n".join(lines)


def structure_phase_stack(
    structure: Structure,
    *,
    n_frames: int = 8,
    device: str = "generic_512",
    wavelength_nm: float = 1550.0,
    grid_size: int | None = None,
) -> tuple[NDArray[np.float64], SLMConfig]:
    """Sweep ``t_frac`` when present; otherwise repeat the static mask."""
    cfg = SLMConfig.from_preset(device)
    n = int(grid_size) if grid_size is not None else min(max(cfg.width, cfg.height), 512)
    half = cfg.extent_mm / 2.0
    x, y = cartesian_grid(n=n, extent=half)
    n_frames = max(int(n_frames), 1)
    frames: list[NDArray[np.float64]] = []
    for i in range(n_frames):
        t_frac = (i + 0.5) / n_frames
        snap = structure.update(t_frac=t_frac) if "t_frac" in structure.params else structure
        mask = snap.to_phase_mask((x, y), wavelength_nm=cfg.wavelength_nm or wavelength_nm)
        frames.append(np.mod(np.angle(mask), 2 * np.pi).astype(np.float64))
    return np.stack(frames, axis=0), cfg


def payload_phase_stack(
    payload: bytes | str,
    *,
    n_frames: int = 8,
    device: str = "generic_512",
    n_orbs: int = 4,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """vqc_demo nested-LG PWM hologram — the coherent sibling of the RGB donuts."""
    import importlib

    _load_vqc_demo()
    slm = importlib.import_module("vqc_demo.slm")
    preset = device if device in slm.SLM_PRESETS else "generic_512"
    cfg = slm.SLMConfig.from_preset(preset)
    stack, meta = slm.phase_sequence(payload, cfg, num_frames=int(n_frames), n_orbs=int(n_orbs))
    meta["device_requested"] = device
    meta["device_used"] = preset
    return np.asarray(stack, dtype=np.float64), meta


def write_playlist(
    stack: NDArray,
    dest: str | Path,
    *,
    cfg: SLMConfig | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write a vqc_demo-shaped SLM folder: phase_stack.npy, PNG/raw frames, manifest."""
    cfg = cfg or SLMConfig.from_preset("generic_512")
    out = ensure_dir(dest)
    frames_dir = ensure_dir(out / "frames")
    stack = np.asarray(stack, dtype=np.float64)
    np.save(out / "phase_stack.npy", stack)
    bit_depth = int(cfg.bit_depth)
    ext = "png" if bit_depth <= 8 else "tiff"
    for i, phase in enumerate(stack):
        levels = phase_to_levels(phase, bit_depth=bit_depth)
        raw = frames_dir / f"phase_{i:04d}.raw"
        raw.write_bytes(np.asarray(levels).tobytes())
        try:
            from PIL import Image

            vis = levels if bit_depth <= 8 else (levels >> (bit_depth - 8)).astype(np.uint8)
            Image.fromarray(np.asarray(vis, dtype=np.uint8), mode="L").save(
                frames_dir / f"phase_{i:04d}.{ext if bit_depth <= 8 else 'png'}"
            )
        except Exception:
            np.save(frames_dir / f"phase_{i:04d}.npy", levels)
    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "vqc_workbench.simulation.hitl.write_playlist",
        "n_phase_frames": int(stack.shape[0]),
        "shape": list(stack.shape),
        "device": {
            "name": cfg.name,
            "width": cfg.width,
            "height": cfg.height,
            "pitch_um": cfg.pitch_um,
            "wavelength_nm": cfg.wavelength_nm,
            "bit_depth": cfg.bit_depth,
        },
        "disclaimer": DISCLAIMER,
    }
    if extra:
        meta.update(extra)
    (out / "manifest.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return out


def run_hitl(
    payload: bytes | str = "I live in Oregon",
    structure: Structure | None = None,
    *,
    device: str = "generic_512",
    channel: str = "projector",
    n_frames: int = 8,
    out: str | Path | None = None,
    full: bool = False,
    capture: str | Path | None = None,
    n_orbs: int = 4,
    wavelength_nm: float = 1550.0,
    grid_size: int | None = None,
) -> HITLResult:
    """Build an SLM playlist and play the payload through the projector proxy."""
    import importlib

    _load_vqc_demo()
    data = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)

    if structure is not None:
        stack, slm_cfg = structure_phase_stack(
            structure,
            n_frames=n_frames,
            device=device,
            wavelength_nm=wavelength_nm,
            grid_size=grid_size,
        )
        extra: dict[str, Any] = {
            "playlist_kind": "structure",
            "structure": structure.summarize(),
        }
    else:
        stack, slm_meta = payload_phase_stack(
            data, n_frames=n_frames, device=device, n_orbs=n_orbs
        )
        try:
            slm_cfg = SLMConfig.from_preset(device)
        except KeyError:
            slm_cfg = SLMConfig.from_preset("generic_512")
        extra = {"playlist_kind": "payload_hologram", "slm_meta": slm_meta}

    playlist_dir = None
    if out is not None:
        playlist_dir = str(write_playlist(stack, Path(out) / "playlist", cfg=slm_cfg, extra=extra))

    pipeline = importlib.import_module("vqc_demo.pipeline")
    projector = importlib.import_module("vqc_demo.projector")
    ch_mod = importlib.import_module("vqc_demo.channel")

    profile = projector.VPL_HW20A if full else projector.TEST_PROFILE
    report: dict[str, Any] = {}
    recovered = b""
    crc_ok = False
    n_proxy = 0
    symbols: list[int] = []
    if capture is not None:
        channel_name = "capture"
        try:
            decoded = pipeline.decode_path(capture, profile=profile, expected=data)
            recovered = bytes(decoded.payload or b"")
            crc_ok = bool(decoded.crc_ok)
            report = dict((decoded.meta or {}).get("report") or {})
            symbols = list(decoded.symbols or [])
        except (ValueError, OSError) as exc:
            report = {"error": str(exc)}
    else:
        apply = channel not in {"", "clean", "none"}
        model = ch_mod.get_preset(channel) if apply else None
        channel_name = channel if apply else "clean"
        try:
            decoded = pipeline.loopback(
                data,
                profile=profile,
                channel=model,
                apply_channel=apply,
            )
            recovered = bytes(decoded.payload or b"")
            crc_ok = bool(decoded.crc_ok)
            report = dict((decoded.meta or {}).get("report") or {})
            symbols = list(decoded.symbols or [])
        except ValueError as exc:
            report = {"error": str(exc)}

    n_proxy = int(report.get("n_frames", 0) or len(symbols) * int(profile.hold_frames))
    match = recovered == data
    bit_errors = int(report.get("bit_errors", 0 if match else max(len(data), len(recovered)) * 8))
    bits_compared = int(report.get("bits_compared", max(len(data), 1) * 8))
    return HITLResult(
        payload=data,
        recovered=recovered,
        payload_match=match,
        crc_ok=crc_ok,
        channel=channel_name,
        profile=str(profile.name),
        n_proxy_frames=n_proxy,
        slm_frames=int(stack.shape[0]),
        playlist_dir=playlist_dir,
        device=slm_cfg.name,
        bit_errors=bit_errors,
        bits_compared=bits_compared,
        report=report,
    )
