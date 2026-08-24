# Hardware-in-the-loop (vqc_demo projector proxy)

Two artifacts, one command. The workbench never pretends a lamp projector
is a coherent OAM transmitter.

```
structure / payload
        │  phase mask (t_frac sweep)  or  vqc_demo nested-LG hologram
        ▼
SLM playlist   phase_stack.npy + frames/phase_XXXX.png|.raw
        │  laser + phase-only panel  (bench handoff)
        │
payload ──► vqc_demo loopback (TEST 320×180 or VPL-HW20A 1080p)
        │  channel: clean | projector | harsh | kolmogorov | bmgl
        ▼
HITLResult  MATCH / CRC / BER + playlist path
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

Decode a filmed capture instead of the in-memory loopback:

```python
hit = wb.hitl("I live in Oregon", capture="path/to/capture.mp4")
```

## CLI

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload "I live in Oregon" --kind spiral_phase --ell 3 --channel projector --out outputs/hitl
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --payload Hi --channel clean
PYTHONPATH=src python3 -m vqc_workbench.cli hitl --capture path/to/frames --payload "I live in Oregon"
```

Default CLI is a one-screen summary. Pass `--json` for the full report.
`--full` switches the proxy to 1920×1080 / 8-frame hold (slow). CI and
interactive runs stay on the 320×180 test profile.

Channel presets come from vqc_demo: `clean`, `projector`, `harsh`,
`kolmogorov`, `bmgl`. They are intensity capture models, not coherent
Kolmogorov screens.

## Playlist layout

```
outputs/hitl/playlist/
  phase_stack.npy
  manifest.json
  frames/phase_0000.png
  frames/phase_0000.raw
  …
```
