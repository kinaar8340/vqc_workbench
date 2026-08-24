# Hardware-in-the-loop (vqc_demo projector proxy)

Two artifacts, one command. The workbench never pretends a lamp projector
is a coherent OAM transmitter.

```
structure / payload
        │
        ├─ phase mask ──► SLM playlist   (laser + phase-only panel)
        │
        └─ vqc_demo encode ──► proxy/frames (+ optional MP4)
                    │              HDMI → VPL-HW20A → camera
                    │                         │
                    ▼                         ▼
              decode files              --capture filmed.mp4
                    └──────────┬──────────────┘
                               ▼
                    HITLResult  MATCH / CRC / BER
```

[vqc_demo](https://github.com/kinaar8340/vqc_demo) owns the intensity RGB
proxy (Sony VPL-HW20A class) and the nested-LG SLM package. This workbench
imports it; **vqc_demo must never import vqc_workbench**.

`vqc_demo` is imported if installed, otherwise `~/Projects/vqc_demo/src` is
added to `sys.path`. Missing the package raises `HITLUnavailable`.

## Honesty

The playlist is **coherent phase**. Load it on a laser + phase-only SLM +
Fourier lens. The projector proxy is **incoherent RGB donuts** that exercise
framing, ring sampling, colour demix, and majority QEC. It is not a
free-space OAM BER. Do not upload projector MP4 frames to the SLM.

## API

```python
from vqc_workbench import Workbench

wb = Workbench()
plate = wb.create_grating(kind="spiral_phase", ell=3)
hit = wb.hitl("I live in Oregon", plate, channel="projector", out="outputs/hitl")
print(hit.summary())
print(hit.payload_match, hit.crc_ok, hit.playlist_dir)
```

Without a structure the playlist is the vqc_demo payload hologram (PWM-gated
LG orbs). With a structure it is that optic's thin-element phase, sweeping
`t_frac` when the kind has one (Orbital Braille).

`--out` writes both the SLM playlist and a projector TX package
(`proxy/frames/`, `manifest.json`, `ffmpeg.sh`). Decode uses those files
(a disk round-trip). Film the stitched MP4 off the VPL-HW20A and pass the
capture back:

```python
hit = wb.hitl("I live in Oregon", plate, out="outputs/hitl", stitch=True)
hit = wb.hitl("I live in Oregon", capture="path/to/capture.mp4")
```

## CLI

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload "I live in Oregon" --kind spiral_phase --ell 3 --channel projector --out outputs/hitl
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload Hi --channel clean --out outputs/hitl
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --capture path/to/capture.mp4 --payload "I live in Oregon"
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload "I live in Oregon" --out outputs/hitl --stitch
```

Default CLI is a one-screen summary. Pass `--json` for the full report.
`--full` switches the proxy to 1920×1080 / 8-frame hold (slow). CI and
interactive runs stay on the 320×180 test profile.

Channel presets come from vqc_demo: `clean`, `projector`, `harsh`,
`kolmogorov`, `bmgl`. They are intensity capture models, not coherent
Kolmogorov screens.

## Playlist layout

```
outputs/hitl/
  playlist/                 # coherent phase (do not play on the lamp projector)
    phase_stack.npy
    frames/phase_0000.png
  proxy/                    # intensity RGB for VPL-HW20A / camera
    frames/frame_00000.png
    manifest.json
    ffmpeg.sh
    vqc_poc.mp4             # only with stitch=True / --stitch
    rx_frames/              # channel-degraded dry-run (if --channel is not clean)
```
