"""Layer-stack RCWA: map a workbench structure onto grcwa / nannos.

The photonic side stays in the workbench. The optional engines own the
Fourier-modal solve. Output is a reconstructed transmitted field that
``pack_oam_result`` turns into ``FullWaveResult`` — not a scalar stand-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from vqc_workbench.core.structure import Structure
from vqc_workbench.utils.grid import cartesian_grid


@dataclass
class LayerSpec:
    name: str
    thickness: float
    epsilon: float | NDArray[np.float64]
    patterned: bool = False


@dataclass
class LayerStack:
    """Periodic stack in the same length units as the workbench grid."""

    period_x: float
    period_y: float
    wavelength: float
    layers: list[LayerSpec]
    Nx: int
    Ny: int
    nG: int = 21
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def patterned(self) -> LayerSpec:
        for layer in self.layers:
            if layer.patterned:
                return layer
        return self.layers[1]


def _rcwa_wavelength(wavelength_nm: float) -> float:
    """Same unit convention as the scalar angular-spectrum backend."""
    return max(float(wavelength_nm) * 1e-6, 0.05)


def _phase_thickness(depth_rad: float, wavelength: float, n_hi: float, n_lo: float) -> float:
    delta = max(float(n_hi) - float(n_lo), 1e-6)
    return float(abs(depth_rad)) * float(wavelength) / (2.0 * np.pi * delta)


def structure_to_stack(
    structure: Structure,
    *,
    wavelength_nm: float = 1550.0,
    grid_size: int = 32,
    extent: float = 4.0,
    nG: int = 21,
    n_hi: float = 1.5,
    n_lo: float = 1.0,
    slab_thickness: float | None = None,
) -> LayerStack:
    """Superstrate / patterned slab / substrate from a workbench structure.

    1-D gratings use one grating period as the unit cell. Other kinds use a
    ``2*extent`` supercell filled from the thin-element phase map.
    """
    lam = _rcwa_wavelength(wavelength_nm)
    n = max(8, min(int(grid_size), 64))
    n_hi = float(n_hi)
    n_lo = float(n_lo)
    kind = structure.kind
    depth = float(structure.params.get("depth_rad", np.pi))
    d = float(slab_thickness) if slab_thickness is not None else _phase_thickness(depth, lam, n_hi, n_lo)
    d = max(d, 0.05 * lam)

    if kind in {"binary_grating", "blazed_grating"}:
        period = float(structure.params.get("period", 0.4))
        angle = np.deg2rad(float(structure.params.get("angle_deg", 0.0)))
        u = np.linspace(0.0, 1.0, n, endpoint=False)
        v = np.linspace(0.0, 1.0, n, endpoint=False)
        U, V = np.meshgrid(u, v, indexing="xy")
        # Unit-cell coordinates in the grating frame.
        x_c = (U - 0.5) * period
        y_c = (V - 0.5) * period
        proj = x_c * np.cos(angle) + y_c * np.sin(angle)
        frac = np.mod(proj / period + 0.5, 1.0)
        if kind == "binary_grating":
            duty = float(structure.params.get("duty", 0.5))
            ep = np.where(frac < duty, n_hi**2, n_lo**2).astype(np.float64)
            depth = float(structure.params.get("depth_rad", np.pi))
        else:
            ep = (n_lo + (n_hi - n_lo) * frac) ** 2
            depth = float(structure.params.get("depth_rad", 2 * np.pi))
        d = float(slab_thickness) if slab_thickness is not None else _phase_thickness(depth, lam, n_hi, n_lo)
        d = max(d, 0.05 * lam)
        px = py = period
        extras = {"unit_cell": "period", "period": period}
    else:
        px = py = 2.0 * float(extent)
        x, y = cartesian_grid(n, float(extent))
        mask = structure.to_phase_mask((x, y), float(wavelength_nm))
        phase = np.mod(np.angle(mask), 2.0 * np.pi)
        n_map = n_lo + (n_hi - n_lo) * (phase / (2.0 * np.pi))
        ep = np.asarray(n_map**2, dtype=np.float64)
        extras = {"unit_cell": "supercell", "extent": float(extent)}

    super_t = 0.5 * lam
    layers = [
        LayerSpec("superstrate", super_t, 1.0, patterned=False),
        LayerSpec("pattern", d, ep, patterned=True),
        LayerSpec("substrate", super_t, 1.0, patterned=False),
    ]
    extras.update(
        {
            "kind": kind,
            "n_hi": n_hi,
            "n_lo": n_lo,
            "slab_thickness": d,
            "wavelength": lam,
            "wavelength_nm": float(wavelength_nm),
        }
    )
    return LayerStack(
        period_x=px,
        period_y=py,
        wavelength=lam,
        layers=layers,
        Nx=n,
        Ny=n,
        nG=int(nG),
        extras=extras,
    )


def _reconstruct_from_orders(
    amps: NDArray,
    kx: NDArray,
    ky: NDArray,
    x: NDArray,
    y: NDArray,
) -> NDArray[np.complex128]:
    field = np.zeros(np.shape(x), dtype=np.complex128)
    amps = np.asarray(amps, dtype=np.complex128).ravel()
    kx = np.real(np.asarray(kx)).ravel()
    ky = np.real(np.asarray(ky)).ravel()
    n = min(amps.size, kx.size, ky.size)
    for g in range(n):
        field += amps[g] * np.exp(1j * (kx[g] * x + ky[g] * y))
    return field


def run_grcwa(
    stack: LayerStack,
    *,
    x: NDArray,
    y: NDArray,
    theta: float = 0.0,
    phi: float = 0.0,
) -> tuple[NDArray[np.complex128], dict[str, Any]]:
    import grcwa

    freq = 1.0 / float(stack.wavelength)
    L1 = [float(stack.period_x), 0.0]
    L2 = [0.0, float(stack.period_y)]
    obj = grcwa.obj(int(stack.nG), L1, L2, freq, float(theta), float(phi), verbose=0)
    ep_blocks = []
    pattern_index = None
    for i, layer in enumerate(stack.layers):
        if layer.patterned:
            ep = np.asarray(layer.epsilon, dtype=float)
            ny, nx = ep.shape
            obj.Add_LayerGrid(float(layer.thickness), int(nx), int(ny))
            # grcwa flatten is (x, y) with indexing ij.
            ep_blocks.append(np.ascontiguousarray(ep.T).ravel())
            pattern_index = i
        else:
            obj.Add_LayerUniform(float(layer.thickness), float(np.mean(layer.epsilon)))
    obj.Init_Setup(Gmethod=1)
    if ep_blocks:
        obj.GridLayer_geteps(np.concatenate(ep_blocks))
    obj.MakeExcitationPlanewave(1.0, 0.0, 0.0, 0.0, order=0)
    R, T = obj.RT_Solve(normalize=1)
    Ri, Ti = obj.RT_Solve(byorder=1)
    which = int(pattern_index if pattern_index is not None else len(stack.layers) - 1)
    z_off = float(stack.layers[which].thickness)
    E_f, _H_f = obj.Solve_FieldFourier(which, z_off)
    # Prefer in-plane Ex (p-pol at normal incidence); fall back to Ez.
    amps = np.asarray(E_f[0], dtype=np.complex128)
    if float(np.max(np.abs(amps))) < 1e-12:
        amps = np.asarray(E_f[2], dtype=np.complex128)
    field = _reconstruct_from_orders(amps, obj.kx, obj.ky, x, y)
    meta = {
        "engine": "grcwa",
        "nG": int(obj.nG),
        "R_total": float(np.real(R)),
        "T_total": float(np.real(T)),
        "T_by_order": np.real(np.asarray(Ti, dtype=float)).tolist(),
        "G": np.asarray(obj.G).tolist(),
        "layer_index": which,
        "polarization": "p",
    }
    return field, meta


def run_nannos(
    stack: LayerStack,
    *,
    x: NDArray,
    y: NDArray,
    theta: float = 0.0,
    phi: float = 0.0,
) -> tuple[NDArray[np.complex128], dict[str, Any]]:
    import nannos as nn

    lattice = nn.Lattice(
        [[float(stack.period_x), 0.0], [0.0, float(stack.period_y)]],
        discretization=(int(stack.Nx), int(stack.Ny)),
    )
    layers = []
    pattern_index = 1
    for i, layer in enumerate(stack.layers):
        eps = layer.epsilon
        if layer.patterned:
            pattern_index = i
            layers.append(
                lattice.Layer(layer.name, thickness=float(layer.thickness), epsilon=np.asarray(eps, dtype=float))
            )
        else:
            eps0 = float(np.mean(eps)) if np.ndim(eps) else float(eps)
            layers.append(lattice.Layer(layer.name, epsilon=eps0))
    pw = nn.PlaneWave(
        float(stack.wavelength),
        angles=(float(np.degrees(theta)), float(np.degrees(phi)), 0.0),
    )
    sim = nn.Simulation(layers, pw, nh=int(stack.nG))
    R, T = sim.diffraction_efficiencies()
    E, _H = sim.get_field_grid(int(pattern_index), z=0)
    E = np.asarray(E)
    if E.ndim == 4 and E.shape[0] == 3:
        Ex = E[0, :, :, 0]
    elif E.ndim == 3 and E.shape[0] == 3:
        Ex = E[0]
    else:
        Ex = np.asarray(E[..., 0] if E.ndim >= 3 else E)
    field = _sample_cell_on_grid(np.asarray(Ex, dtype=np.complex128), stack.period_x, stack.period_y, x, y)
    meta = {
        "engine": "nannos",
        "nG": int(stack.nG),
        "R_total": float(np.real(R)),
        "T_total": float(np.real(T)),
        "layer_index": int(pattern_index),
        "polarization": "p",
    }
    return field, meta


def _sample_cell_on_grid(
    cell: NDArray,
    period_x: float,
    period_y: float,
    x: NDArray,
    y: NDArray,
) -> NDArray[np.complex128]:
    from scipy.ndimage import map_coordinates

    cell = np.asarray(cell, dtype=np.complex128)
    ny, nx = cell.shape[:2]
    gx = np.mod(np.asarray(x, dtype=float), float(period_x)) / float(period_x) * (nx - 1)
    gy = np.mod(np.asarray(y, dtype=float), float(period_y)) / float(period_y) * (ny - 1)
    real = map_coordinates(np.real(cell), [gy, gx], order=1, mode="wrap")
    imag = map_coordinates(np.imag(cell), [gy, gx], order=1, mode="wrap")
    return (real + 1j * imag).astype(np.complex128)
