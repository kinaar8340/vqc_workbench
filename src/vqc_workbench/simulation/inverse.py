"""Inverse design: search structure parameters for a target charge or fidelity.

The inner loop is the **modal** engine (fast). Meep remains a validation
backend, not the optimizer's inner loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Callable, Literal

import numpy as np

from vqc_workbench.core.structure import Structure
from vqc_workbench.structures.charge import forecast_charge
from vqc_workbench.ui.editors import schema_for

Objective = Literal["charge", "forecast", "fidelity"]


@dataclass
class InverseResult:
    kind: str
    objective: str
    params: dict[str, Any]
    score: float
    n_evals: int
    metrics: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "objective": self.objective,
            "params": self.params,
            "score": self.score,
            "n_evals": self.n_evals,
            "metrics": self.metrics,
        }


def _schema_space(kind: str, names: list[str] | None = None) -> list[dict[str, Any]]:
    fields = schema_for(kind)
    if names:
        wanted = set(names)
        fields = [f for f in fields if f["name"] in wanted]
    if not fields:
        raise ValueError(f"no searchable parameters for kind {kind!r}")
    return fields


def _cast(field: dict[str, Any], value: float) -> int | float:
    if field["type"] == "int":
        return int(round(value))
    return float(value)


def _grid(fields: list[dict[str, Any]], max_evals: int) -> list[dict[str, Any]]:
    axes: list[list[Any]] = []
    for f in fields:
        lo, hi = f["min"], f["max"]
        if f["type"] == "int":
            axes.append(list(range(int(lo), int(hi) + 1)))
        else:
            n = min(7, max(3, int(max_evals ** (1 / max(len(fields), 1)))))
            axes.append(list(np.linspace(float(lo), float(hi), n)))
    combos = []
    for values in product(*axes):
        combos.append({f["name"]: _cast(f, v) for f, v in zip(fields, values)})
        if len(combos) >= max_evals:
            break
    return combos


class InverseDesigner:
    """Search a structure's parameter box against charge or VQC fidelity."""

    def __init__(
        self,
        workbench: Any,
        *,
        L_max: int = 8,
        grid_size: int = 64,
        max_evals: int = 256,
    ):
        self.wb = workbench
        self.L_max = int(L_max)
        self.grid_size = int(grid_size)
        self.max_evals = int(max_evals)

    def evaluate(
        self,
        structure: Structure,
        *,
        objective: Objective = "charge",
        target_ell: int | None = None,
        payload: bytes = b"Hi",
        compensate: bool = False,
    ) -> tuple[float, dict[str, Any]]:
        """Return (score, metrics). Lower score is better."""
        modes = self.wb.simulate_modes(structure, L_max=self.L_max, grid_size=self.grid_size)
        dominant = int(modes.dominant_ell())
        expectation = float(modes.expectation_ell())
        purity = float((modes.intensity**2).sum())
        forecast = forecast_charge(structure)
        metrics: dict[str, Any] = {
            "dominant_ell": dominant,
            "expectation_ell": expectation,
            "purity": purity,
            "forecast_ell": forecast.expected_ell,
            "params": dict(structure.params),
        }

        if objective == "fidelity":
            result = self.wb.run_vqc(
                structure,
                payload,
                L_max=self.L_max,
                grid_size=self.grid_size,
                qec_reps=1,
                turbulence=0.0,
                n_z=4,
                compensate=compensate,
            )
            metrics["fidelity"] = float(result.fidelity)
            metrics["payload_match"] = bool(result.payload_match)
            return float(1.0 - result.fidelity), metrics

        if target_ell is None:
            raise ValueError(f"objective={objective!r} requires target_ell")

        if objective == "forecast":
            pred = forecast.expected_ell
            if pred is None:
                return 1e6, metrics
            # Analytic match first, then prefer high measured purity at that charge.
            charge_err = abs(int(pred) - int(target_ell))
            meas_err = abs(dominant - int(target_ell))
            score = 10.0 * charge_err + meas_err + (1.0 - purity)
            return float(score), metrics

        # objective == "charge": measured OAM vs target.
        score = (
            abs(dominant - int(target_ell))
            + 0.25 * abs(expectation - float(target_ell))
            + (1.0 - purity)
        )
        return float(score), metrics

    def optimize(
        self,
        kind: str,
        *,
        objective: Objective = "charge",
        target_ell: int | None = None,
        payload: bytes = b"Hi",
        compensate: bool = False,
        param_names: list[str] | None = None,
        seed_params: dict[str, Any] | None = None,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> InverseResult:
        if param_names is None and objective in {"charge", "forecast"}:
            ints = [f["name"] for f in schema_for(kind) if f["type"] == "int"]
            if ints:
                param_names = ints
        fields = _schema_space(kind, param_names)
        candidates = _grid(fields, self.max_evals)
        seed = dict(seed_params or {})
        if seed:
            candidates.insert(0, {**{f["name"]: seed.get(f["name"], f["default"]) for f in fields}})

        history: list[dict[str, Any]] = []
        best_score = float("inf")
        best_params: dict[str, Any] | None = None
        best_metrics: dict[str, Any] = {}

        seen: set[tuple] = set()
        for params in candidates:
            key = tuple(sorted((k, params[k]) for k in params))
            if key in seen:
                continue
            seen.add(key)
            structure = self.wb.create_structure(kind, **params)
            score, metrics = self.evaluate(
                structure,
                objective=objective,
                target_ell=target_ell,
                payload=payload,
                compensate=compensate,
            )
            row = {"score": score, **metrics}
            history.append(row)
            if callback is not None:
                callback(row)
            if score < best_score:
                best_score = score
                best_params = dict(params)
                best_metrics = metrics

        if best_params is None:
            raise RuntimeError("inverse design produced no evaluations")
        return InverseResult(
            kind=kind,
            objective=objective,
            params=best_params,
            score=best_score,
            n_evals=len(history),
            metrics=best_metrics,
            history=history,
        )
