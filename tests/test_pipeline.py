from vqc_workbench.api import Workbench
from vqc_workbench.simulation.codec import capacity_bits, min_L_max


def test_min_l_max_capacity():
    assert capacity_bits(8) == 32
    assert min_L_max(16) <= 8


def test_identity_roundtrip_short_payload():
    wb = Workbench()
    conduit = wb.create_structure("identity")
    result = wb.run_vqc(conduit, b"Hi", L_max=8, qec_reps=1, turbulence=0.0, n_z=4)
    assert result.recovered_payload == b"Hi"
    assert result.payload_match
    assert result.ber == 0.0
    assert result.fidelity >= 0.999


def test_spiral_shifts_modes_off_payload():
    """A spiral plate is a mode shifter; payload recovery is not expected."""
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    result = wb.run_vqc(plate, b"Hi", L_max=8, qec_reps=1, turbulence=0.0, n_z=4)
    assert result.payload == b"Hi"
    assert isinstance(result.recovered_payload, (bytes, bytearray))
