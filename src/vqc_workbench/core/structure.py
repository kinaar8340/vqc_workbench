"""Abstract editable photonic structure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.materials import Material
from vqc_workbench.utils.io import dump_yaml, load_yaml


class Structure(ABC):
    """Editable photonic structure: grating, metasurface, shell, lattice, …"""

    kind: str = "structure"

    def __init__(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        material: Material | None = None,
    ):
        self.name = name
        self.params: dict[str, Any] = dict(params or {})
        self.material = material

    @abstractmethod
    def to_phase_mask(
        self,
        grid: tuple[NDArray, NDArray],
        wavelength_nm: float,
    ) -> NDArray[np.complex128]:
        """Complex thin-element transmission on (x, y)."""

    def to_geometry_dict(self) -> dict[str, Any]:
        """Serializable description for full-wave backends or export."""
        return {
            "kind": self.kind,
            "name": self.name,
            "params": deepcopy(self.params),
            "material": None if self.material is None else self.material.summarize(),
        }

    def update(self, **new_params: Any) -> Structure:
        """Immutable-style update — returns a new instance of the same class."""
        merged = {**self.params, **new_params}
        return self.__class__(name=self.name, params=merged, material=self.material)

    def summarize(self) -> dict[str, Any]:
        return self.to_geometry_dict()

    def to_yaml(self, path: str | Path) -> Path:
        payload = {
            "kind": self.kind,
            "name": self.name,
            "params": deepcopy(self.params),
            "material": None if self.material is None else self.material.name,
        }
        return dump_yaml(payload, path)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Structure:
        from vqc_workbench.core.registry import structure_from_spec

        return structure_from_spec(load_yaml(path))


class ParametricCell(Structure):
    """Convenience base for a small set of continuous/discrete parameters."""

    kind: str = "parametric"

    def to_phase_mask(
        self,
        grid: tuple[NDArray, NDArray],
        wavelength_nm: float,
    ) -> NDArray[np.complex128]:
        raise NotImplementedError
