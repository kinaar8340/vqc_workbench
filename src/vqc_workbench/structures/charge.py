"""Expected topological charge from structure parameters.

The dashboard and CLI print this next to the measured OAM peak so the
arithmetic is visible (e.g. trajectoid ℓ = winding − n_trenches).
"""

from __future__ import annotations

from dataclasses import dataclass

from vqc_workbench.core.structure import Structure


@dataclass(frozen=True)
class ChargeForecast:
    expected_ell: int | None
    formula: str
    mode_shifter: bool
    notes: str = ""

    def as_dict(self) -> dict[str, int | str | bool | None]:
        return {
            "expected_ell": self.expected_ell,
            "formula": self.formula,
            "mode_shifter": self.mode_shifter,
            "notes": self.notes,
        }


def forecast_charge(structure: Structure) -> ChargeForecast:
    """Return the topological charge implied by ``structure.params``."""
    kind = structure.kind
    p = structure.params

    if kind == "spiral_phase":
        ell = int(p.get("ell", 1))
        return ChargeForecast(ell, f"ℓ = ell = {ell:+d}", True, "Pure helical phase plate.")

    if kind == "forked_hologram":
        ell = int(p.get("ell", 1))
        return ChargeForecast(
            ell,
            f"ℓ = ell = {ell:+d}",
            True,
            "Near-field LG projection is spread by the linear carrier; demodulate to recover ℓ.",
        )

    if kind == "trajectoid":
        n = int(p.get("n_trenches", 8))
        winding = int(p.get("winding", 2))
        ell = winding - n
        return ChargeForecast(
            ell,
            f"ℓ = winding − n_trenches = {winding:+d} − {n} = {ell:+d}",
            True,
            "Jacobi–Anger: e^{i(wφ + a cos(nφ))} ≈ Σ J_k(a) e^{i(w+kn)φ}; "
            "a = π/2 and the Gaussian aperture select the k = −1 branch.",
        )

    if kind == "metasurface":
        ell = int(p.get("ell_target", 0))
        return ChargeForecast(
            ell,
            f"ℓ = ell_target = {ell:+d}",
            ell != 0,
            "Helical bias on an otherwise free phase map.",
        )

    if kind == "flux_lattice":
        ell = int(p.get("ell", 3))
        return ChargeForecast(ell, f"ℓ = ell = {ell:+d}", True, "Helical carrier on the vortex ring.")

    if kind == "identity":
        return ChargeForecast(0, "ℓ = 0", False, "Recovery channel.")

    if kind in {"binary_grating", "blazed_grating"}:
        return ChargeForecast(
            0,
            "ℓ = 0 (no topological charge)",
            False,
            "1-D grating. The OAM projector may pick a noisy peak; ⟨ℓ⟩ ≈ 0.",
        )

    if kind == "orbital_braille":
        return ChargeForecast(None, "multimode (PWM orbs)", False, "Not a pure shifter.")

    if kind == "matched_filter":
        inner = p.get("target_kind")
        return ChargeForecast(
            None,
            f"inverse of {inner or 'target'}",
            True,
            "Conjugate phase / reciprocal amplitude of the target optic.",
        )

    if kind == "cascade":
        return ChargeForecast(None, "product of stages", False, "Net charge is the sum of stage charges.")

    return ChargeForecast(None, "no closed-form charge", False, "")
