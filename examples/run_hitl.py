#!/usr/bin/env python3
"""SLM playlist from a spiral plate, then vqc_demo projector-proxy loopback."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    result = wb.hitl(
        "I live in Oregon",
        plate,
        channel="projector",
        n_frames=8,
        out="outputs/hitl",
    )
    print(result.summary())


if __name__ == "__main__":
    main()
