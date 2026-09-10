"""Workbench Hopf / quaternion primitives must match flux_hopf_lib."""

from flux_hopf_lib.hopf import hopf_map_quaternion
from flux_hopf_lib.quaternion import Quaternion as LibQuaternion

from vqc_workbench.core.geometry import Quaternion, flux_hopf_available, hopf_map


def test_quaternion_is_lib_class():
    assert Quaternion is LibQuaternion
    assert flux_hopf_available() is True


def test_hopf_map_matches_lib_classical():
    q = Quaternion(0.0, 0.0, 1.0, 0.0)
    y = hopf_map(q)
    assert tuple(y.tolist()) == (0.0, 0.0, -1.0)
    lib = hopf_map_quaternion(q.w, q.x, q.y, q.z)
    assert y.tolist() == list(lib)
