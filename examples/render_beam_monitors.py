"""Generate cached dual-monitor PNGs for the 16-frame prototype mapping."""

from __future__ import annotations

from pathlib import Path

from vqc_workbench.core.config import workbench_root
from vqc_workbench.ladder.frames import MONITOR_ASSETS, load_monitor_asset, render_monitor_set


def _contact_sheet(path: Path) -> None:
    from matplotlib.image import imsave

    import numpy as np

    order = [
        ("initial", "axial"),
        ("initial", "st"),
        ("slm", "axial"),
        ("slm", "st"),
        ("helical", "axial"),
        ("helical", "st"),
        ("detect", "axial"),
        ("detect", "st"),
    ]
    tiles = [load_monitor_asset(s, v) for s, v in order]
    h = max(t.shape[0] for t in tiles)
    w = max(t.shape[1] for t in tiles)
    pad = []
    for t in tiles:
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        y0 = (h - t.shape[0]) // 2
        x0 = (w - t.shape[1]) // 2
        canvas[y0 : y0 + t.shape[0], x0 : x0 + t.shape[1]] = t
        pad.append(canvas)
    row1 = np.concatenate(pad[0:4], axis=1)
    row2 = np.concatenate(pad[4:8], axis=1)
    sheet = np.concatenate([row1, row2], axis=0)
    imsave(path, sheet)
    print(f"wrote {path}")


def main() -> None:
    root = workbench_root()
    pkg = Path(__file__).resolve().parents[1] / "src" / "vqc_workbench" / "assets" / "beam_monitors"
    docs = root / "docs" / "figures" / "beam_monitors"
    written = render_monitor_set()
    print(f"wrote {len(MONITOR_ASSETS)} monitor pairs")
    print(f"  package: {pkg}")
    print(f"  docs:    {docs}")
    for key, path in written.items():
        print(f"  {key}: {path}")
    _contact_sheet(docs / "contact_sheet.png")


if __name__ == "__main__":
    main()
