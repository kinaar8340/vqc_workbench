from vqc_workbench.api import Workbench


def test_matched_filter_recovers_spiral_payload():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=3)
    raw = wb.run_vqc(plate, b"Hi", L_max=8, qec_reps=1, turbulence=0.0, n_z=4)
    assert raw.payload_match is False

    recovered = wb.run_vqc(
        plate, b"Hi", L_max=8, qec_reps=1, turbulence=0.0, n_z=4, compensate=True
    )
    assert recovered.recovered_payload == b"Hi"
    assert recovered.payload_match
    assert recovered.metrics["compensated"] is True


def test_cascade_with_matched_filter_is_near_identity():
    wb = Workbench()
    plate = wb.create_grating(kind="spiral_phase", ell=2)
    compensated = wb.compensate(plate)
    modes = wb.simulate_modes(compensated, L_max=6, grid_size=64)
    assert modes.dominant_ell() == 0
    assert float(modes.intensity[modes.ell == 0][0]) > 0.7
