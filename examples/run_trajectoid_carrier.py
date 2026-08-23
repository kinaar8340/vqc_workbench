#!/usr/bin/env python3
"""Trajectoid trench shell + identity VQC payload round-trip."""

from vqc_workbench import Workbench


def main() -> None:
    wb = Workbench()
    shell = wb.create_trajectoid(payload_hash="I live in Oregon", winding=2)
    modes = wb.simulate_modes(shell, L_max=8)
    print(f"trajectoid dominant_ell={modes.dominant_ell()}")

    conduit = wb.create_structure("identity")
    result = wb.run_vqc(conduit, b"Hi", L_max=8, qec_reps=1, turbulence=0.0)
    print(
        f"VQC identity channel  fidelity={result.fidelity:.4f}  "
        f"BER={result.ber:.4f}  recovered={result.recovered_payload!r}"
    )


if __name__ == "__main__":
    main()
