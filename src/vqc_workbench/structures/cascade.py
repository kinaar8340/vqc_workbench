"""Cascade and matched-filter structures.

A thin-element matched filter is the inverse transmission of a target
structure (conjugate phase, reciprocal amplitude). Cascading
``target * matched_filter(target)`` recovers an identity channel, which is
how payload recovery works after a known mode shifter such as a spiral plate.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.registry import register
from vqc_workbench.core.structure import ParametricCell, Structure


def inverse_mask(mask: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Pointwise inverse of a complex thin-element transmission."""
    amp = np.abs(mask)
    out = np.zeros_like(mask, dtype=np.complex128)
    nz = amp > 1e-12
    out[nz] = np.conj(mask[nz]) / (amp[nz] ** 2)
    return out


@register("matched_filter")
class MatchedFilter(ParametricCell):
    """Inverse thin-element of ``target`` — a matched filter / inverse shifter."""

    kind = "matched_filter"

    def __init__(
        self,
        name: str = "matched_filter",
        params: dict[str, Any] | None = None,
        material=None,
        target: Structure | None = None,
    ):
        params = dict(params or {})
        if target is None:
            target = _target_from_params(params)
        if target is None:
            raise ValueError("matched_filter requires a target structure")
        self.target = target
        params["target_kind"] = target.kind
        params["target_params"] = dict(target.params)
        super().__init__(name=name or f"matched_{target.kind}", params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        return inverse_mask(self.target.to_phase_mask(grid, wavelength_nm))

    def update(self, **new_params: Any) -> Structure:
        merged = {**self.params, **new_params}
        return MatchedFilter(
            name=self.name,
            params=merged,
            material=self.material,
            target=self.target,
        )

    def to_geometry_dict(self) -> dict[str, Any]:
        spec = super().to_geometry_dict()
        spec["target"] = self.target.summarize()
        return spec


@register("cascade")
class Cascade(ParametricCell):
    """Product of thin-element transmissions, applied in order."""

    kind = "cascade"

    def __init__(
        self,
        name: str = "cascade",
        params: dict[str, Any] | None = None,
        material=None,
        stages: list[Structure] | None = None,
    ):
        params = dict(params or {})
        stages = list(stages or [])
        if not stages:
            raise ValueError("cascade requires at least one stage")
        self.stages = stages
        params["n_stages"] = len(stages)
        params["stage_kinds"] = [s.kind for s in stages]
        super().__init__(name=name, params=params, material=material)

    def to_phase_mask(self, grid, wavelength_nm: float) -> NDArray[np.complex128]:
        x, _y = grid
        field = np.ones_like(x, dtype=np.complex128)
        for stage in self.stages:
            field = field * stage.to_phase_mask(grid, wavelength_nm)
        return field

    def update(self, **new_params: Any) -> Structure:
        merged = {**self.params, **new_params}
        return Cascade(name=self.name, params=merged, material=self.material, stages=self.stages)

    def to_geometry_dict(self) -> dict[str, Any]:
        spec = super().to_geometry_dict()
        spec["stages"] = [s.summarize() for s in self.stages]
        return spec


def compensate_structure(structure: Structure) -> Cascade:
    """Return ``structure`` followed by its matched filter (≈ identity)."""
    return Cascade(
        name=f"compensated_{structure.kind}",
        stages=[structure, MatchedFilter(target=structure)],
    )


def _target_from_params(params: dict[str, Any]) -> Structure | None:
    kind = params.get("target_kind")
    if not kind:
        return None
    from vqc_workbench.core.registry import get_structure_class

    cls = get_structure_class(str(kind))
    nested = dict(params.get("target_params") or {})
    return cls(name=str(kind), params=nested)
