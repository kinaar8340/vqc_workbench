"""Bind the default photonic ladder and write a static HMI figure."""

from __future__ import annotations

from pathlib import Path

from vqc_workbench.ladder import LadderEngine, beam_evolution_ladder
from vqc_workbench.ladder.render import render_ladder


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "docs" / "figures" / "ladder_hmi.png"
    doc = beam_evolution_ladder()
    doc.cycle = 42
    runtime = LadderEngine(grid_size=int(doc.grid_size)).bind(doc)
    render_ladder(doc, runtime, out)
    spec = runtime.spectrum
    print(f"wrote {out}")
    print(f"rungs={len(doc.rungs)} selected={doc.selected_node_id} peak={spec.peak_label}")


if __name__ == "__main__":
    main()
