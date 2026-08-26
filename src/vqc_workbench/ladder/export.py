"""Plain-text PLC instruction-list export of a photonic ladder (documentation)."""

from __future__ import annotations

from pathlib import Path

from vqc_workbench.ladder.model import LadderDocument


def export_instruction_list(doc: LadderDocument) -> str:
    """Allen-Bradley-style listing. Not a vendor download — lab documentation."""
    lines = [
        f"TITLE     {doc.title}",
        f"VERSION   {doc.version}",
        f"LAMBDA    {doc.wavelength_nm:.1f} nm",
        f"SCAN      {'ACTIVE' if doc.scan_active else 'HALT'}",
        "",
    ]
    for rung in doc.rungs:
        lines.append(f"NETWORK {rung.number:02d}  {rung.title}  // {rung.subtitle}  WB {rung.workbench.get('kind', 'identity')}")
        for contact in rung.contacts:
            if contact.kind == "NC":
                op = "XIO"
            elif contact.kind == "trigger":
                op = "ONS"
            elif contact.kind == "param":
                op = "MOV"
            else:
                op = "XIC"
            extra = f"  {contact.value}" if contact.kind == "param" and contact.value else ""
            lines.append(f"  {op}   {contact.tag}{extra}")
        coil = f"{rung.id.upper()}_BEAM"
        lines.append(f"  OTE   {coil}")
        if rung.equipment:
            lines.append("  // EQUIPMENT  " + " -> ".join(d.tag for d in rung.equipment))
        lines.append("")
    return "\n".join(lines) + "\n"


def write_instruction_list(doc: LadderDocument, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(export_instruction_list(doc), encoding="utf-8")
    return p
