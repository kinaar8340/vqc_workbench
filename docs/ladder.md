# Photonic Ladder Diagram

PLC / SCADA / HMI workbench for photonic pipelines. Rungs are sequential
stages of the VQC Prototype pulsed-beam evolution; coils are live beam
monitors; a dedicated **EQUIPMENT / LAB MAPPING** strip sits **directly
under** each logic rung (never side-by-side).

```
┌──────────────────────────────────────────────────────────────────┐
│  TITLE / STATUS BAR                                              │
│  Photonic Ladder Diagram – Beam Evolution + Lab Mapping          │
│  | VQC Workbench vX.Y.Z                                          │
│  RUNG SCAN: ACTIVE  •  CYCLE: NNNNN  •  EDIT MODE                │
├──────────────────────────────────────────────────────────────────┤
│  SPECTRUM ANALYZER — Selected Node Signal          (full width)  │
│  Intensity vs ℓ or λ   |   NODE / PEAK ℓ / FWHM                  │
├──────────────────────────────────────────────────────────────────┤
│  LOGIC RUNG 01  (full width)   contacts + dual beam monitors     │
│  EQUIPMENT / LAB MAPPING 01  (full width, never beside logic)    │
├──────────────────────────────────────────────────────────────────┤
│  LOGIC RUNG 02  …                                                │
│  EQUIPMENT / LAB MAPPING 02                                      │
├──────────────────────────────────────────────────────────────────┤
│  …                                                               │
└──────────────────────────────────────────────────────────────────┘
```

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Data | YAML ladder program (`configs/ladders/`) | Same family as workbench structure YAML; can drive `Workbench()` |
| Engine | Python `LadderEngine` on `Workbench` | Modal OAM, phase masks, propagate, SLM / VQC / HITL |
| Static HMI | matplotlib (`ladder.render`) | Headless industrial mock-up / docs figure / CI |
| Interactive HMI | Streamlit + injected industrial CSS | Already the workbench UI extra; no Electron |
| Beam panels | numpy RGB scientific monitors | Intensity / phase LUTs, not marketing renders |

Not chosen: Qt / Electron / Three.js. The existing Streamlit dashboard
and Python API are the native surface; the ladder is another view of the
same façade, not a second stack.

## Data model

- **Rung** = one beam-evolution stage (`initial`, `slm`, `helical`, `detect`).
- **Contact / tag** = control signal (`NO`, `NC`, `trigger`, `param`).
- **Coil** → two side-by-side monitors: axial / phase-front and
  spatiotemporal / length.
- **Equipment row** = physical bench map with `[TAG]` fields.
- **Selected node** glows `#00FF00` until that node is triggered or
  another node is selected. The spectrum analyzer tracks the selection.

Default program: 16-frame pulsed-beam sequence mapped onto four rungs.

| Rung | Axial (prototype frames) | Spatiotemporal | Workbench kind | Lab mapping |
|------|--------------------------|----------------|----------------|-------------|
| 1 INITIAL | FR 1–3 collimated pulse | FR 4–5 pulse streak | `identity` | 532 nm laser, expander, dice, L1, iris |
| 2 SLM | FR 6–8 vortex / spiral phase | FR 9–10 helical length | `spiral_phase` | SLM, HWP λ/2, L3, GPD |
| 3 HELICAL | FR 11–12 nested wavefronts | FR 13 twisted tubes | `trajectoid` | rotating diffuser, L4, LCP |
| 4 DETECT | FR 14–15 dense rings | FR 16 nested stack | `spiral_phase` ell=3 | Cam1 CCD, Cam2 EMCCD, fiber, analysis node |

## Module map

```
ui/ladder.py  (Streamlit HMI)
ladder/render.py  (static matplotlib HMI)
        │
        ▼
ladder/engine.py  ──► Workbench()  create_structure / simulate_modes /
        │                           export_slm / run_vqc / hitl
        ▼
ladder/model.py   YAML ⇄ LadderDocument
ladder/frames.py  scientific RGB monitors
```

`vqc_workbench` still **imports** the ecosystem and never the reverse.
The ladder does not import `vqc_proto/src/photonics.py`.

## Run

```bash
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --render docs/figures/ladder_hmi.png
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --json
PYTHONPATH=src python3 -m vqc_workbench.cli ladder --port 8502   # Streamlit; needs [ui]
```

Python:

```python
from vqc_workbench.ladder import LadderEngine, beam_evolution_ladder, save_ladder
from vqc_workbench.ladder.render import render_ladder

doc = beam_evolution_ladder()
rt = LadderEngine(grid_size=64).bind(doc)
render_ladder(doc, rt, "outputs/ladder_hmi.png")
save_ladder(doc, "outputs/ladder.yaml")
```

## Selection / glow

- Any contact, rail, equipment tag, or beam monitor is a node.
- Selection is single-node. The selected node uses persistent
  `#00FF00` outline + soft outer glow.
- Glow remains until `trigger(node_id)` fires on that node, or another
  node is selected.
- Spectrum analyzer updates to the selected node’s signal (OAM ℓ
  spectrum, or λ for `[LASER_532]`).

## Visual rules (do not break)

- Dark industrial gray, subtle grid, flat panels, sharp corners.
- Classic PLC symbols (open/closed contacts, vertical rails).
- Editable tags with gear marks; green ACTIVE diamonds.
- Accent color only for active / selected (`#00FF00`) and status LEDs.
- Dual beam panels look like lab monitors (scale, frame label, color bar).
- No marketing gloss, no rounded product-card layout.

## Phase gates

1. Architecture + YAML model + this document.
2. Hierarchical layout (title → spectrum → stacked logic+equipment).
3. Dual beam monitors on the right of every logic rung.
4. Equipment rows associated under each rung, full width.
5. Spectrum analyzer + `#00FF00` persistent selection glow.
6. Live `Workbench()` binding (modes, masks, optional SLM / VQC / HITL).
7. Edit / add / delete / reorder rungs; save/load YAML; cycle / scan.
8. Tooltips, README, static figure `docs/figures/ladder_hmi.png`.

## Future

- Multi-user shared ladder programs.
- Live HITL: selected `[SLM_01]` pushes the current mask; cameras
  replace synthetic detect-stage frames.
- Export contacts as PLC instruction lists (documentation only unless
  a lab PLC is on the bench).
