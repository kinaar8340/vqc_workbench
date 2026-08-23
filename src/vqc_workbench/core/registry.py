"""Structure kind → class registry (plugin dict; entry points later)."""

from __future__ import annotations

from typing import Any, Callable, Type

from vqc_workbench.core.materials import Material, MaterialLibrary
from vqc_workbench.core.structure import Structure

_REGISTRY: dict[str, Type[Structure]] = {}


def register(kind: str) -> Callable[[Type[Structure]], Type[Structure]]:
    def deco(cls: Type[Structure]) -> Type[Structure]:
        cls.kind = kind
        _REGISTRY[kind] = cls
        return cls

    return deco


def get_structure_class(kind: str) -> Type[Structure]:
    if kind not in _REGISTRY:
        # Importing structures populates the registry.
        import vqc_workbench.structures  # noqa: F401

    if kind not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY)) or "(none registered)"
        raise KeyError(f"unknown structure kind {kind!r}; known: {known}")
    return _REGISTRY[kind]


def available_kinds() -> list[str]:
    import vqc_workbench.structures  # noqa: F401

    return sorted(_REGISTRY)


def structure_from_spec(
    spec: dict[str, Any],
    materials: MaterialLibrary | None = None,
) -> Structure:
    kind = str(spec.get("kind") or spec.get("type") or "")
    cls = get_structure_class(kind)
    mat_name = spec.get("material")
    material: Material | None = None
    if isinstance(mat_name, str):
        material = (materials or MaterialLibrary()).get(mat_name)
    elif isinstance(mat_name, dict):
        material = Material(
            name=str(mat_name.get("name", "custom")),
            n=complex(mat_name.get("n", 1.0)),
            k=float(mat_name.get("k", 0.0)),
        )
    params = dict(spec.get("params") or {})
    name = str(spec.get("name") or f"{kind}")
    return cls(name=name, params=params, material=material)
