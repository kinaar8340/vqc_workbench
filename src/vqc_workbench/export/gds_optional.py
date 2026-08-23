"""Optional gdsfactory hook — reserved for PIC tape-out later."""

from __future__ import annotations

from typing import Any


def gdsfactory_available() -> bool:
    try:
        import gdsfactory  # noqa: F401

        return True
    except Exception:
        return False


def export_gds(geometry: dict[str, Any], path: str) -> str:
    if not gdsfactory_available():
        raise RuntimeError(
            "gdsfactory is not installed. This hook is reserved for a later PIC / "
            "foundry PDK path; the modal + SLM workbench does not require it."
        )
    raise NotImplementedError("GDS export is a Phase-later hook; see docs/architecture.md")
