"""Live oam_flux lattice coupling: OAM coefficients → gauged Hopf flywheels.

The photonic side stays in the workbench modal engine. oam_flux owns the
twist lattice, flux deposition, gauge torque, and back-reaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import Structure
from vqc_workbench.simulation.modal import ModeResult, ModalSimulator


class LatticeUnavailable(RuntimeError):
    pass


def _load_oam_flux():
    try:
        from vqc_workbench.adapters import import_oam_flux

        return import_oam_flux()
    except ImportError as exc:
        raise LatticeUnavailable(
            "oam_flux is not importable. pip install -e ../oam_flux "
            "or keep the checkout at ~/Projects/oam_flux."
        ) from exc


@dataclass
class LatticeCouplingResult:
    ell: int
    kappa: float
    steps: int
    nx: int
    initial_mean_twist: float
    final_mean_twist: float
    twist_variance: float
    coupling_factor: float
    ell_shift: float
    conservation_residual: float
    oam_before: dict[int, float]
    oam_after: dict[int, float]
    history: list[dict[str, float]] = field(default_factory=list)
    sweep: list[dict[str, Any]] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ell": self.ell,
            "kappa": self.kappa,
            "steps": self.steps,
            "nx": self.nx,
            "initial_mean_twist": self.initial_mean_twist,
            "final_mean_twist": self.final_mean_twist,
            "twist_variance": self.twist_variance,
            "coupling_factor": self.coupling_factor,
            "ell_shift": self.ell_shift,
            "conservation_residual": self.conservation_residual,
            "oam_before": {str(k): v for k, v in self.oam_before.items() if v > 1e-6},
            "oam_after": {str(k): v for k, v in self.oam_after.items() if v > 1e-6},
            "history": self.history,
            "sweep": self.sweep,
        }


def _oam_dict(ells: NDArray, intensity: NDArray) -> dict[int, float]:
    return {int(e): float(i) for e, i in zip(ells, intensity)}


def apply_oam_backaction(
    ells: NDArray,
    intensity: NDArray,
    *,
    ell: int,
    coupling_factor: float,
    ell_shift: float,
) -> NDArray[np.float64]:
    """Scale the driven mode and leak a fraction into a neighbor (ℓ-shift)."""
    out = np.asarray(intensity, dtype=np.float64).copy()
    idx = np.where(ells == int(ell))[0]
    if idx.size == 0:
        return out
    i0 = int(idx[0])
    factor = float(np.clip(coupling_factor, 0.0, 1.0))
    out[i0] *= factor
    leak = min(abs(float(ell_shift)), 0.25) * out[i0]
    neighbor = int(ell) + int(np.sign(ell_shift) or 1)
    j = np.where(ells == neighbor)[0]
    if leak > 0 and j.size:
        out[i0] = max(0.0, out[i0] - leak)
        out[int(j[0])] += leak
    total = float(out.sum())
    if total > 0:
        out /= total
    return out


def _pack_propagation(modes: ModeResult, z_prop, rho, radial_weights, w0: float, wavelength_nm: float):
    import importlib

    vp = importlib.import_module("oam_flux.vqc_photonics")
    PhotonicsConfig = vp.PhotonicsConfig
    OFProp = vp.PropagationResult
    l_max = int(modes.L_max)
    cfg = PhotonicsConfig(
        l_max=l_max,
        w0=float(w0),
        lambda_nm=float(wavelength_nm),
        nr=int(len(rho)),
        n_z=int(z_prop.n_z if hasattr(z_prop, "n_z") else len(z_prop.z_steps)),
        z_start=float(z_prop.z_steps[0]),
        z_end=float(z_prop.z_steps[-1]),
    )
    return OFProp(
        z_steps=np.asarray(z_prop.z_steps, dtype=float),
        ells=np.asarray(z_prop.ells),
        intensity=np.asarray(z_prop.intensity, dtype=float),
        rho=np.asarray(rho, dtype=float),
        radial_weights=np.asarray(radial_weights, dtype=float),
        config=cfg,
    )


def couple_modes_to_lattice(
    modes: ModeResult,
    modal: ModalSimulator,
    *,
    kappa: float = 0.85,
    steps: int = 8,
    ell: int | None = None,
    nx: int = 12,
    kick_strength: float = 0.08,
    flywheel_sites: int = 4,
    sweep_kappa: list[float] | None = None,
    w0: float | None = None,
    wavelength_nm: float | None = None,
) -> LatticeCouplingResult:
    of = _load_oam_flux()
    import importlib

    TwistLattice = importlib.import_module("oam_flux.lattice").TwistLattice
    vqc_coupling = importlib.import_module("oam_flux.vqc_coupling")
    VQCCouplingState = vqc_coupling.VQCCouplingState
    run_vqc_coupling_step = vqc_coupling.run_vqc_coupling_step
    lattice_back_reaction = importlib.import_module("oam_flux.back_reaction").lattice_back_reaction
    oam_kinetic_momentum = importlib.import_module("oam_flux.momentum").oam_kinetic_momentum

    ell = int(ell if ell is not None else modes.dominant_ell())
    w0 = float(w0 if w0 is not None else modal.config.w0)
    wavelength_nm = float(wavelength_nm if wavelength_nm is not None else modal.config.wavelength_nm)
    n_z = max(int(steps), 4)
    z_prop = modal.propagate(modes, n_z=n_z, turbulence=0.0)
    weights, rho = modal.radial_weights(L_max=modes.L_max, nr=128, w0=w0)
    of_prop = _pack_propagation(modes, z_prop, rho, weights, w0, wavelength_nm)

    kappas = [float(kappa)] if not sweep_kappa else [float(k) for k in sweep_kappa]
    sweep_rows: list[dict[str, Any]] = []
    last_state = None
    last_br = None
    last_lattice = None
    initial_twist = 0.0

    for kap in kappas:
        lattice = TwistLattice(nx=int(nx), kappa=float(kap))
        initial_twist = float(lattice.mean_twist)
        p0 = float(oam_kinetic_momentum(energy_scale=1.0, ell=ell, lambda_nm=wavelength_nm))
        state = VQCCouplingState(
            lattice=lattice,
            propagation=of_prop,
            ell=ell,
            kick_strength=float(kick_strength),
            flywheel_sites=int(flywheel_sites),
            photon_reservoir=p0,
            initial_total_momentum=p0,
        )
        for step in range(int(steps)):
            run_vqc_coupling_step(state, step)
        br = lattice_back_reaction(lattice, ell=ell)
        last_state, last_br, last_lattice = state, br, lattice
        sweep_rows.append(
            {
                "kappa": float(kap),
                "final_mean_twist": float(lattice.mean_twist),
                "twist_variance": float(lattice.twist_variance),
                "coupling_factor": float(br["coupling_factor"]),
                "ell_shift": float(br["effective_ell_shift"]),
                "conservation_residual": float(state.history[-1]["conservation_residual"])
                if state.history
                else 0.0,
            }
        )

    assert last_state is not None and last_br is not None and last_lattice is not None
    oam_before = _oam_dict(modes.ell, modes.intensity)
    oam_after_arr = apply_oam_backaction(
        modes.ell,
        modes.intensity,
        ell=ell,
        coupling_factor=float(last_br["coupling_factor"]),
        ell_shift=float(last_br["effective_ell_shift"]),
    )
    residual = float(last_state.history[-1]["conservation_residual"]) if last_state.history else 0.0
    return LatticeCouplingResult(
        ell=ell,
        kappa=float(kappas[-1] if sweep_kappa else kappa),
        steps=int(steps),
        nx=int(nx),
        initial_mean_twist=initial_twist,
        final_mean_twist=float(last_lattice.mean_twist),
        twist_variance=float(last_lattice.twist_variance),
        coupling_factor=float(last_br["coupling_factor"]),
        ell_shift=float(last_br["effective_ell_shift"]),
        conservation_residual=residual,
        oam_before=oam_before,
        oam_after=_oam_dict(modes.ell, oam_after_arr),
        history=list(last_state.history),
        sweep=sweep_rows if sweep_kappa else None,
    )
