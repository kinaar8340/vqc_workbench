"""Static industrial PLC / HMI render of a photonic ladder (matplotlib)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from vqc_workbench.ladder.engine import LadderRuntime, SpectrumReadout
from vqc_workbench.ladder.frames import _INTENSITY_LUT, colorbar_strip
from vqc_workbench.ladder.model import SELECT_GLOW, EquipmentDevice, LadderDocument, Rung

BG = "#1a1d21"
PANEL = "#23272e"
PANEL2 = "#2a2f37"
BORDER = "#4c5360"
RAIL = "#c5ccd4"
TEXT = "#c8ced6"
MUTED = "#7d8693"
LED = "#3dcc7a"
ACCENT = "#3d7a9b"
BEVEL = "#16191d"
GRID = "#2e333c"


def _rgb01(arr) -> np.ndarray:
    a = np.asarray(arr)
    if a.dtype == np.uint8:
        return a.astype(np.float64) / 255.0
    return np.clip(a, 0.0, 1.0)


def render_ladder(
    doc: LadderDocument,
    runtime: LadderRuntime | None = None,
    path: str | Path | None = None,
    *,
    dpi: int = 110,
) -> Any:
    """Draw the full hierarchical HMI. Returns a matplotlib Figure."""
    import matplotlib.pyplot as plt

    n_rungs = max(1, len(doc.rungs))
    fig_h = 7.2 + 3.35 * n_rungs
    fig = plt.figure(figsize=(22.0, fig_h), facecolor=BG, dpi=dpi)
    fig.subplots_adjust(0, 0, 1, 1)
    ax = fig.add_axes([0, 0, 1, 1], facecolor=BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    ax.set_clip_on(False)

    title_h = 0.038 * (18.0 / fig_h) * 2.2
    title_h = min(0.055, max(0.032, 0.72 / fig_h))
    spec_h = min(0.16, max(0.11, 2.15 / fig_h))
    y_cursor = 1.0
    y_cursor = _draw_title(ax, doc, y1=y_cursor, h=title_h)
    spec = None if runtime is None else runtime.spectrum
    y_cursor = _draw_spectrum(fig, ax, doc, spec, y1=y_cursor, h=spec_h)

    remain = y_cursor - 0.012
    block_h = remain / n_rungs
    logic_h = block_h * 0.62
    equip_h = block_h * 0.38

    for i, rung in enumerate(doc.rungs):
        y1 = y_cursor - i * block_h
        state = None if runtime is None else runtime.rungs.get(rung.id)
        _draw_logic_rung(fig, ax, doc, rung, state, y1=y1, h=logic_h)
        _draw_equipment(ax, doc, rung, y1=y1 - logic_h, h=equip_h)

    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, facecolor=fig.get_facecolor(), dpi=dpi)
    return fig


def _panel(ax, x, y, w, h, fc=PANEL, ec=BORDER, lw=0.8):
    from matplotlib.patches import Rectangle

    r = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=1)
    ax.add_patch(r)
    return r


def _txt(ax, x, y, s, *, size=8, color=TEXT, ha="left", va="center", weight="normal"):
    ax.text(
        x,
        y,
        s,
        color=color,
        fontsize=size,
        ha=ha,
        va=va,
        fontfamily="DejaVu Sans Mono",
        fontweight=weight,
        zorder=5,
        clip_on=False,
    )


def _glow(ax, x, y, w, h, selected: bool):
    from matplotlib.patches import Rectangle

    if not selected:
        return
    ax.add_patch(
        Rectangle(
            (x - 0.002, y - 0.004),
            w + 0.004,
            h + 0.008,
            facecolor=SELECT_GLOW,
            edgecolor="none",
            alpha=0.12,
            zorder=4,
        )
    )
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor="none",
            edgecolor=SELECT_GLOW,
            linewidth=1.6,
            zorder=6,
        )
    )


def _selected(doc: LadderDocument, node_id: str) -> bool:
    return bool(doc.selected_node_id) and doc.selected_node_id == node_id


def _draw_title(ax, doc: LadderDocument, y1: float, h: float) -> float:
    y0 = y1 - h
    _panel(ax, 0.012, y0, 0.976, h, fc="#1e2228", ec=BORDER, lw=1.0)
    title = f"{doc.title} | VQC Workbench v{doc.version}"
    _txt(ax, 0.022, y0 + h * 0.55, title, size=10.5, weight="bold", color="#d5dbe3")
    scan = "ACTIVE" if doc.scan_active else "HALT"
    scan_c = LED if doc.scan_active else "#c45c4a"
    edit = "EDIT MODE" if doc.edit_mode else "RUN MODE"
    _txt(ax, 0.72, y0 + h * 0.55, "RUNG SCAN:", size=8.5, color=MUTED, ha="right")
    _txt(ax, 0.728, y0 + h * 0.55, scan, size=8.5, color=scan_c, ha="left", weight="bold")
    _txt(ax, 0.84, y0 + h * 0.55, f"CYCLE: {int(doc.cycle):05d}", size=8.5, color=TEXT, ha="center")
    _txt(ax, 0.975, y0 + h * 0.55, edit, size=8.5, color=ACCENT, ha="right")
    return y0


def _draw_spectrum(
    fig,
    ax,
    doc: LadderDocument,
    spec: SpectrumReadout | None,
    y1: float,
    h: float,
) -> float:
    y0 = y1 - h
    _panel(ax, 0.012, y0, 0.976, h, fc=PANEL, ec=BORDER)
    _txt(
        ax,
        0.022,
        y1 - 0.018,
        "SPECTRUM ANALYZER  —  Selected Node Signal",
        size=8.5,
        color=MUTED,
        va="top",
    )
    if spec is None:
        _txt(ax, 0.5, y0 + h * 0.42, "(bind ladder to Workbench for live spectrum)", size=8, color=MUTED, ha="center")
        return y0

    sax = fig.add_axes([0.03, y0 + 0.018, 0.72, h - 0.042], facecolor="#16191d")
    sax.tick_params(colors=MUTED, labelsize=7)
    for spine in sax.spines.values():
        spine.set_color(BORDER)
        spine.set_linewidth(0.6)
    sax.yaxis.label.set_color(MUTED)
    sax.xaxis.label.set_color(MUTED)
    sax.set_ylabel("INTENSITY", fontsize=7, fontfamily="DejaVu Sans Mono")
    xlabel = "MODE  ell" if spec.axis == "ell" else "WAVELENGTH  nm"
    sax.set_xlabel(xlabel, fontsize=7, fontfamily="DejaVu Sans Mono")
    x = np.asarray(spec.x)
    y = np.asarray(spec.y)
    if spec.axis == "ell":
        sax.bar(x, y, width=0.78, color="#3d8a6a", edgecolor="#1e3d32", linewidth=0.4, zorder=2)
        sax.set_xlim(float(x.min()) - 0.6, float(x.max()) + 0.6)
    else:
        sax.plot(x, y, color="#6ec4a8", lw=1.3, zorder=2)
        sax.fill_between(x, y, color="#3d8a6a", alpha=0.35, zorder=1)
    sax.set_ylim(0, max(1.05 * float(np.max(y) if y.size else 1.0), 0.08))
    sax.grid(True, axis="y", color=GRID, lw=0.5)
    sax.set_axisbelow(True)

    # readout
    rx, rw = 0.77, 0.20
    _panel(ax, rx, y0 + 0.02, rw, h - 0.045, fc="#1c2026", ec=BORDER)
    lines = [
        f"NODE  {spec.node_name}",
        f"PEAK  {spec.peak_label}",
        f"FWHM  {spec.fwhm:.2f}",
        f"AXIS  {spec.axis}",
    ]
    if spec.extras.get("expectation_ell") is not None:
        lines.append(f"<ell> {float(spec.extras['expectation_ell']):+.2f}")
    if spec.extras.get("expected_ell") is not None:
        lines.append(f"FCST  ell={int(spec.extras['expected_ell']):+d}")
    for i, line in enumerate(lines):
        _txt(ax, rx + 0.01, y0 + h - 0.055 - i * 0.022, line, size=8, color=TEXT)
    return y0


def _draw_logic_rung(fig, ax, doc: LadderDocument, rung: Rung, state, y1: float, h: float) -> None:
    y0 = y1 - h
    x0, w = 0.012, 0.976
    _panel(ax, x0, y0, w, h, fc=PANEL, ec=BORDER)
    # header strip
    _panel(ax, x0, y1 - 0.022, w, 0.022, fc="#1e2329", ec=BORDER, lw=0.6)
    _txt(
        ax,
        x0 + 0.008,
        y1 - 0.011,
        f"RUNG {rung.number:02d}  {rung.title}   {rung.subtitle}",
        size=8,
        color=MUTED,
    )
    if state is not None and state.dominant_ell is not None:
        _txt(
            ax,
            x0 + w - 0.01,
            y1 - 0.011,
            f"WB {state.kind}  ell={state.dominant_ell:+d}",
            size=7.5,
            color=ACCENT,
            ha="right",
        )

    # rails
    inner_y0 = y0 + 0.012
    inner_y1 = y1 - 0.030
    mid_y = 0.5 * (inner_y0 + inner_y1)
    rail_x_l = x0 + 0.012
    mon_w = 0.168
    gap = 0.008
    rail_x_r = x0 + w - 0.010
    mon2_x = rail_x_r - 0.006 - mon_w
    mon1_x = mon2_x - gap - mon_w
    ax.plot([rail_x_l, rail_x_l], [inner_y0, inner_y1], color=RAIL, lw=2.2, solid_capstyle="butt", zorder=3)
    ax.plot([rail_x_r, rail_x_r], [inner_y0, inner_y1], color=RAIL, lw=2.2, solid_capstyle="butt", zorder=3)
    _glow(ax, rail_x_l - 0.004, inner_y0, 0.008, inner_y1 - inner_y0, _selected(doc, f"{rung.id}.rail_l"))
    _glow(ax, rail_x_r - 0.004, inner_y0, 0.008, inner_y1 - inner_y0, _selected(doc, f"{rung.id}.rail_r"))

    # rung line
    ax.plot([rail_x_l, mon1_x - 0.006], [mid_y, mid_y], color=RAIL, lw=1.4, zorder=3)

    contacts = rung.contacts
    n_c = max(1, len(contacts))
    usable = (mon1_x - 0.03) - (rail_x_l + 0.02)
    slot = usable / n_c
    for i, c in enumerate(contacts):
        cx = rail_x_l + 0.028 + (i + 0.5) * slot
        nid = c.node_id(rung.id)
        _draw_contact(ax, cx, mid_y, c, selected=_selected(doc, nid))

    # dual monitors (replace coil)
    axial = None if state is None else state.axial
    st = None if state is None else state.spatiotemporal
    _draw_monitor(
        fig,
        ax,
        mon1_x,
        inner_y0,
        mon_w,
        inner_y1 - inner_y0,
        rgb=axial,
        monitor=rung.axial,
        selected=_selected(doc, rung.axial.node_id(rung.id) if rung.axial else ""),
    )
    _draw_monitor(
        fig,
        ax,
        mon2_x,
        inner_y0,
        mon_w,
        inner_y1 - inner_y0,
        rgb=st,
        monitor=rung.spatiotemporal,
        selected=_selected(doc, rung.spatiotemporal.node_id(rung.id) if rung.spatiotemporal else ""),
    )
    # short links into monitors
    ax.plot([mon1_x - 0.006, mon1_x], [mid_y, mid_y], color=RAIL, lw=1.4, zorder=3)


def _draw_contact(ax, cx: float, cy: float, contact, *, selected: bool) -> None:
    from matplotlib.patches import Polygon, Rectangle

    w, h = 0.078, 0.072
    x, y = cx - w / 2, cy - h / 2
    _glow(ax, x, y, w, h, selected)
    # tag plate
    ax.add_patch(
        Rectangle((x + 0.004, cy + 0.012), w - 0.008, 0.020, facecolor="#1c2026", edgecolor=BORDER, lw=0.7, zorder=4)
    )
    _txt(ax, cx, cy + 0.022, contact.tag, size=6.4, ha="center", color="#d2d8e0")
    # contact symbol
    gap = 0.007
    ax.plot([cx - 0.018, cx - gap], [cy - 0.006, cy - 0.006], color=RAIL, lw=1.3, zorder=5)
    ax.plot([cx + gap, cx + 0.018], [cy - 0.006, cy - 0.006], color=RAIL, lw=1.3, zorder=5)
    ax.plot([cx - gap, cx - gap], [cy - 0.018, cy + 0.006], color=RAIL, lw=1.5, zorder=5)
    ax.plot([cx + gap, cx + gap], [cy - 0.018, cy + 0.006], color=RAIL, lw=1.5, zorder=5)
    if contact.kind == "NC":
        ax.plot([cx - gap - 0.002, cx + gap + 0.002], [cy - 0.018, cy + 0.008], color=RAIL, lw=1.1, zorder=5)
    if contact.kind == "trigger":
        ax.plot([cx, cx], [cy - 0.018, cy - 0.028], color=ACCENT, lw=1.0, zorder=5)
        ax.plot([cx - 0.006, cx, cx + 0.006], [cy - 0.024, cy - 0.028, cy - 0.024], color=ACCENT, lw=1.0, zorder=5)
    if contact.kind == "param" and contact.value:
        _txt(ax, cx, cy - 0.030, str(contact.value), size=6, ha="center", color=ACCENT)
    # LED diamond
    led = LED if contact.closed else "#3a4048"
    d = 0.006
    ax.add_patch(
        Polygon(
            [(cx, cy + 0.038 + d), (cx + d, cy + 0.038), (cx, cy + 0.038 - d), (cx - d, cy + 0.038)],
            closed=True,
            facecolor=led,
            edgecolor="#1a1d21",
            lw=0.4,
            zorder=6,
        )
    )
    # gear
    _txt(ax, x + w - 0.006, y + h - 0.008, "⚙", size=7, ha="right", color=MUTED, va="top")


def _draw_monitor(fig, ax, x, y, w, h, *, rgb, monitor, selected: bool) -> None:
    from matplotlib.patches import Rectangle

    _glow(ax, x, y, w, h, selected)
    ax.add_patch(Rectangle((x, y), w, h, facecolor=BEVEL, edgecolor=BORDER, lw=0.9, zorder=3))
    title = "MONITOR" if monitor is None else monitor.title
    scale = "" if monitor is None else monitor.scale
    flabel = "" if monitor is None else monitor.frame_label()
    _txt(ax, x + 0.004, y + h - 0.012, title, size=6.2, color=MUTED)
    _txt(ax, x + w - 0.004, y + h - 0.012, flabel, size=6.2, color=ACCENT, ha="right")
    # image area in figure coords — ax is 0-1 so add_axes uses same
    img_x = x + 0.006
    img_y = y + 0.018
    img_w = w - 0.028
    img_h = h - 0.034
    iax = fig.add_axes([img_x, img_y, img_w, img_h], facecolor="#0c0e10")
    iax.set_xticks([])
    iax.set_yticks([])
    for spine in iax.spines.values():
        spine.set_color("#0a0c0e")
    if rgb is not None:
        iax.imshow(_rgb01(rgb), origin="upper", interpolation="bilinear", aspect="equal")
    else:
        iax.set_facecolor("#0c0e10")
        iax.text(0.5, 0.5, "NO SIG", color=MUTED, ha="center", va="center", fontsize=8, fontfamily="DejaVu Sans Mono")
    # colorbar
    cax = fig.add_axes([x + w - 0.018, img_y, 0.008, img_h], facecolor=BEVEL)
    cax.set_xticks([])
    cax.set_yticks([])
    for spine in cax.spines.values():
        spine.set_color(BORDER)
        spine.set_linewidth(0.4)
    strip = colorbar_strip(_INTENSITY_LUT, height=64, width=8)
    cax.imshow(_rgb01(strip), origin="upper", aspect="auto")
    _txt(ax, x + 0.004, y + 0.008, scale, size=5.6, color=MUTED)


def _draw_equipment(ax, doc: LadderDocument, rung: Rung, y1: float, h: float) -> None:
    from matplotlib.patches import Rectangle

    y0 = y1 - h
    x0, w = 0.012, 0.976
    _panel(ax, x0, y0, w, h, fc="#1f242b", ec=BORDER)
    _panel(ax, x0, y1 - 0.018, w, 0.018, fc="#1a1f25", ec=BORDER, lw=0.6)
    _txt(ax, x0 + 0.008, y1 - 0.009, "EQUIPMENT / LAB MAPPING", size=7.5, color=MUTED)
    devices = rung.equipment
    n = max(1, len(devices))
    pad = 0.016
    slot = (w - 2 * pad) / n
    cy = y0 + (h - 0.018) * 0.42
    xs = []
    for i, dev in enumerate(devices):
        cx = x0 + pad + (i + 0.5) * slot
        xs.append(cx)
        nid = dev.node_id(rung.id)
        _draw_device(ax, cx, cy, h * 0.55, dev, selected=_selected(doc, nid))
    # green signal-flow
    if len(xs) >= 2:
        ax.plot(xs, [cy + 0.01] * len(xs), color=LED, lw=1.2, zorder=2, alpha=0.85)
        for cx in xs:
            ax.plot(cx, cy + 0.01, marker="o", color=LED, markersize=3.2, zorder=3)


def _draw_device(ax, cx: float, cy: float, s: float, dev: EquipmentDevice, *, selected: bool) -> None:
    from matplotlib.patches import Rectangle

    bw, bh = 0.118, min(0.078, s + 0.028)
    x, y = cx - bw / 2, cy - bh / 2
    _glow(ax, x, y, bw, bh, selected)
    ax.add_patch(Rectangle((x, y), bw, bh, facecolor="#252a32", edgecolor=BORDER, lw=0.8, zorder=3))
    _draw_icon(ax, dev.kind, cx, cy + 0.008, 0.028)
    _txt(ax, cx, y + 0.014, dev.tag, size=7.2, ha="center", color="#d8dee6")
    _txt(ax, cx, y + bh - 0.009, dev.name, size=6.0, ha="center", color=MUTED, va="top")
    _txt(ax, x + bw - 0.004, y + bh - 0.006, "⚙", size=6.5, ha="right", color=MUTED, va="top")


def _draw_icon(ax, kind: str, cx: float, cy: float, s: float) -> None:
    from matplotlib.patches import Circle, Rectangle, Polygon, Ellipse

    c = "#9aa3b0"
    k = kind.lower()
    if k == "laser":
        ax.add_patch(Rectangle((cx - s, cy - 0.35 * s), 1.1 * s, 0.7 * s, fill=False, edgecolor=c, lw=0.9, zorder=5))
        ax.plot([cx + 0.15 * s, cx + s], [cy, cy], color=LED, lw=1.3, zorder=5)
    elif k == "expander":
        ax.plot([cx - s, cx - 0.2 * s], [cy - 0.45 * s, cy], color=c, lw=0.9, zorder=5)
        ax.plot([cx - s, cx - 0.2 * s], [cy + 0.45 * s, cy], color=c, lw=0.9, zorder=5)
        ax.plot([cx + 0.2 * s, cx + s], [cy, cy - 0.45 * s], color=c, lw=0.9, zorder=5)
        ax.plot([cx + 0.2 * s, cx + s], [cy, cy + 0.45 * s], color=c, lw=0.9, zorder=5)
    elif k == "lens":
        ax.add_patch(Ellipse((cx, cy), 0.45 * s, 1.3 * s, fill=False, edgecolor=c, lw=0.9, zorder=5))
    elif k == "iris":
        ax.add_patch(Circle((cx, cy), 0.55 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        ax.add_patch(Circle((cx, cy), 0.22 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
    elif k == "slm":
        ax.add_patch(Rectangle((cx - 0.7 * s, cy - 0.5 * s), 1.4 * s, s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        for t in (-0.25, 0.25):
            ax.plot([cx - 0.7 * s, cx + 0.7 * s], [cy + t * s, cy + t * s], color=c, lw=0.5, zorder=5)
            ax.plot([cx + t * s, cx + t * s], [cy - 0.5 * s, cy + 0.5 * s], color=c, lw=0.5, zorder=5)
    elif k in {"hwp", "polarizer"}:
        ax.add_patch(Circle((cx, cy), 0.55 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        ax.text(cx, cy, "λ/2" if k == "hwp" else "P", color=c, ha="center", va="center", fontsize=5.5, zorder=5, fontfamily="DejaVu Sans Mono")
    elif k == "camera":
        ax.add_patch(Rectangle((cx - 0.7 * s, cy - 0.4 * s), 1.1 * s, 0.8 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        ax.add_patch(Circle((cx + 0.55 * s, cy), 0.28 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
    elif k == "fiber":
        ax.plot([cx - s, cx + s], [cy, cy], color=LED, lw=1.1, zorder=5)
        ax.plot([cx - 0.3 * s, cx + 0.3 * s], [cy + 0.12 * s, cy + 0.12 * s], color=c, lw=0.7, zorder=5)
    elif k == "node":
        ax.add_patch(
            Polygon(
                [(cx, cy + 0.55 * s), (cx + 0.55 * s, cy), (cx, cy - 0.55 * s), (cx - 0.55 * s, cy)],
                fill=False,
                edgecolor=LED,
                lw=0.9,
                zorder=5,
            )
        )
    elif k == "diffuser":
        ax.add_patch(Circle((cx, cy), 0.55 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        ax.plot([cx - 0.4 * s, cx + 0.4 * s], [cy - 0.2 * s, cy + 0.2 * s], color=c, lw=0.6, zorder=5)
        ax.plot([cx - 0.4 * s, cx + 0.4 * s], [cy + 0.2 * s, cy - 0.2 * s], color=c, lw=0.6, zorder=5)
    elif k == "stage":
        ax.add_patch(Rectangle((cx - 0.8 * s, cy - 0.25 * s), 1.6 * s, 0.2 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
        ax.plot([cx, cx], [cy - 0.25 * s, cy - 0.55 * s], color=c, lw=0.8, zorder=5)
    elif k == "detector":
        ax.add_patch(Polygon([(cx - 0.5 * s, cy - 0.4 * s), (cx + 0.5 * s, cy), (cx - 0.5 * s, cy + 0.4 * s)], fill=False, edgecolor=c, lw=0.8, zorder=5))
    else:
        ax.add_patch(Rectangle((cx - 0.5 * s, cy - 0.35 * s), s, 0.7 * s, fill=False, edgecolor=c, lw=0.8, zorder=5))
