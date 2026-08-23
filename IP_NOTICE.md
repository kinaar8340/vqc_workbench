# Intellectual Property Notice

**VQC Photonic Workbench** (`vqc_workbench`)  
Copyright © 2026 Aaron Michael Kinder

The workbench *integration layer* (structure editor, modal coupling, YAML
configs, dashboard shell, optional full-wave wrappers) is released under the
MIT License. See [`LICENSE`](LICENSE).

## Downstream VQC / patent constraints

This package is designed to **import** the existing VQC family. It does **not**
re-implement the patented Vortex Quaternion Conduit pipeline. When you enable
optional extras that wrap those repos, **their licenses apply to that path**:

| Repository | License (as published) | Notes |
|------------|------------------------|--------|
| `vqc_proto`, `vqc_sims_public` | CC-BY-NC-SA-4.0 + patent restrictions | US Provisional 63/913,110 |
| `vqc_demo` | see that repo | intensity-proxy / SLM POC |
| `flux_hopf_lib` | MIT | quaternion / Hopf / flux primitives |
| `oam_flux`, `flux_trajectoid`, `hfb`, `qga` | see those repos | lattice, shells, optics, geometry |

Permitted for the VQC extras: non-commercial research with attribution.  
Commercial use, sublicensing, or production deployment of the VQC core requires
a written license from the patent holder.

Contact: kinaar0@protonmail.com

## Dependency direction

`vqc_workbench` imports the ecosystem. The ecosystem must **never** import
`vqc_workbench`. Optional backends are discovered at runtime and degrade
gracefully when a package is absent.
