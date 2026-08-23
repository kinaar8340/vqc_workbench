"""Material library: n(λ), optional extinction and anisotropy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from vqc_workbench.core.config import workbench_root
from vqc_workbench.utils.io import load_yaml


IndexFn = Callable[[float], complex]


@dataclass
class Material:
    name: str
    n: complex | float | IndexFn
    k: float = 0.0
    wavelength_nm: float | None = None
    anisotropy: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def index(self, wavelength_nm: float) -> complex:
        if callable(self.n):
            return complex(self.n(wavelength_nm))
        return complex(self.n) + 1j * float(self.k)

    def summarize(self) -> dict[str, Any]:
        n0 = self.index(self.wavelength_nm or 1550.0)
        return {
            "name": self.name,
            "n": n0.real,
            "k": n0.imag,
            "wavelength_nm": self.wavelength_nm,
            "anisotropy": self.anisotropy,
        }


class MaterialLibrary:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else (
            workbench_root() / "configs" / "materials" / "library.yaml"
        )
        self._items: dict[str, Material] = {}
        if self.path.is_file():
            self._load(self.path)

    def _load(self, path: Path) -> None:
        raw = load_yaml(path)
        for name, spec in raw.items():
            if not isinstance(spec, dict):
                continue
            self._items[name] = Material(
                name=name,
                n=complex(spec.get("n", 1.0)),
                k=float(spec.get("k", 0.0)),
                wavelength_nm=spec.get("wavelength_nm"),
                anisotropy=spec.get("anisotropy"),
                extras={k: v for k, v in spec.items() if k not in {"n", "k", "wavelength_nm", "anisotropy"}},
            )

    def get(self, name: str | Material | None, default: str = "fused_silica") -> Material:
        if isinstance(name, Material):
            return name
        key = name or default
        if key in self._items:
            return self._items[key]
        if default in self._items:
            return self._items[default]
        return Material(name=key or "air", n=1.0)

    def names(self) -> list[str]:
        return sorted(self._items)

    def __contains__(self, name: str) -> bool:
        return name in self._items
