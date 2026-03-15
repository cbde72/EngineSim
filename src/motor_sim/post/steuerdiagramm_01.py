from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import transforms


PHASE_FONT = 6
TICK_FONT = 6
AXIS_LABEL_FONT = 8
SUMMARY_FONT = 6
EVENT_LABEL_FONT = 6
EVENT_LINEWIDTH = 0.45
EVENT_COLOR = "0.55"
VOLUME_COLOR = "0.25"
OVERLAP_COLOR = "0.78"
POLAR_TEXT_FONT = 6
POLAR_AXIS_FONT = 8


def _phase_segments(cycle_deg: float, angle_ref_mode: str) -> list[tuple[float, float, str]]:
    mode = str(angle_ref_mode).upper().strip()
    if abs(float(cycle_deg) - 720.0) > 1e-9:
        return []
    if mode == "GAS_EXCHANGE_TDC":
        return [
            (-360.0, -180.0, "Ansaugen"),
            (-180.0, 0.0, "Verdichten"),
            (0.0, 180.0, "Arbeiten"),
            (180.0, 360.0, "Ausschieben"),
        ]
    return [
        (-360.0, -180.0, "Arbeiten"),
        (-180.0, 0.0, "Ausschieben"),
        (0.0, 180.0, "Ansaugen"),
        (180.0, 360.0, "Verdichten"),
    ]


def _wrap_to_window(theta_deg: np.ndarray, xmin: float, xmax: float, cycle_deg: float) -> np.ndarray:
    center = 0.5 * (xmin + xmax)
    return ((theta_deg - center + 0.5 * cycle_deg) % cycle_deg) - 0.5 * cycle_deg + center


def _prepare_xy(df, column: str, xmin: float, xmax: float, cycle_deg: float) -> tuple[np.ndarray, np.ndarray] | None:
    if column not in df.columns or "theta_deg" not in df.columns:
        return None
    theta_raw = df["theta_deg"].to_numpy(dtype=float)
    values = df[column].to_numpy(dtype=float)
    mask = np.isfinite(theta_raw) & np.isfinite(values)
    if not np.any(mask):
        return None
    theta = _wrap_to_window(theta_raw[mask], xmin, xmax, cycle_deg)
    values = values[mask]
    order = np.argsort(theta)
    theta = theta[order]
    values = values[order]
    unique_theta, unique_idx = np.unique(theta, return_index=True)
    values = values[unique_idx]
    return unique_theta, values


def _add_phase_labels(ax, xmin: float, xmax: float, cycle_deg: float, angle_ref_mode: str):
    segs = _phase_segments(cycle_deg, angle_ref_mode)
    if not segs:
        return
    trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for a0, a1, label in segs:
        left = max(a0, xmin)
        right = min(a1, xmax)
        if right <= left:
            continue
        xc = 0.5 * (left + right)
        ax.text(
            xc,
            -0.22,
            label,
            transform=trans,
            ha="center",
            va="top",
            fontsize=PHASE_FONT,
            clip_on=False,
        )


def _format_event_lines(events: dict, overlap: dict | None = None, slot_events: dict | None = None) -> list[str]:
    lines: list[str] = []
    for key in ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg"):
        if key in events:
            lines.append(f"{key.replace('_deg', '')}: {float(events[key]):.1f} °KW")
    if "intake_duration_deg" in events:
        lines.append(f"Einlassdauer: {float(events['intake_duration_deg']):.1f} °KW")
    if "exhaust_duration_deg" in events:
        lines.append(f"Auslassdauer: {float(events['exhaust_duration_deg']):.1f} °KW")
    if overlap and overlap.get("total_overlap_deg") is not None:
        lines.append(f"Overlap: {float(overlap['total_overlap_deg']):.1f} °KW")
    if slot_events:
        for key, label in (
            ("INT_OPEN_deg", "INT open"),
            ("INT_CLOSE_deg", "INT close"),
            ("EXH_OPEN_deg", "EXH open"),
            ("EXH_CLOSE_deg", "EXH close"),
        ):
            if key in slot_events:
                lines.append(f"{label}: {float(slot_events[key]):.1f} °KW")
    return lines


def _event_positions(events: dict, xmin: float, xmax: float, cycle_deg: float) -> list[tuple[float, str, float]]:
    items = []
    for key, label in (("IVO_deg", "IVO"), ("IVC_deg", "IVC"), ("EVO_deg", "EVO"), ("EVC_deg", "EVC")):
        if key in events:
            x = _wrap_to_window(np.array([float(events[key])]), xmin, xmax, cycle_deg)[0]
            items.append((x, label, float(events[key])))
    return sorted(items, key=lambda x: x[0])


def _draw_event_labels(ax, ax2, events: dict, xmin: float, xmax: float, cycle_deg: float):
    items = _event_positions(events, xmin, xmax, cycle_deg)
    if not items:
        return
    y0, y1 = ax2.get_ylim()
    yr = max(y1 - y0, 1.0)
    base = y1 + 0.06 * yr
    min_dx = max((xmax - xmin) * 0.055, 18.0)
    levels = [0.0, 0.09 * yr, 0.18 * yr, 0.27 * yr]
    placed_x: list[float] = []
    label_pos: list[tuple[float, float, str]] = []
    for x, label, _raw in items:
        level_idx = 0
        if placed_x and abs(x - placed_x[-1]) < min_dx:
            level_idx = min(len(placed_x), len(levels) - 1)
        y = base + levels[level_idx]
        label_pos.append((x, y, label))
        placed_x.append(x)
    ax2.set_ylim(y0, max(y1, base + max(levels) + 0.08 * yr))
    for x, y, label in label_pos:
        ax2.annotate(
            label,
            xy=(x, y0 + 0.985 * (ax2.get_ylim()[1] - y0)),
            xytext=(x, y),
            textcoords="data",
            ha="center",
            va="bottom",
            fontsize=EVENT_LABEL_FONT,
            color=EVENT_COLOR,
            arrowprops=dict(arrowstyle="-", color=EVENT_COLOR, lw=0.35, shrinkA=0, shrinkB=0),
            clip_on=False,
        )


def _normalize_segments(segments, xmin: float, xmax: float, cycle_deg: float) -> list[tuple[float, float]]:
    norm: list[tuple[float, float]] = []
    for a0, a1 in segments or []:
        a0w = _wrap_to_window(np.array([float(a0)]), xmin, xmax, cycle_deg)[0]
        a1w = _wrap_to_window(np.array([float(a1)]), xmin, xmax, cycle_deg)[0]
        if a1w < a0w:
            if xmax > a0w:
                norm.append((a0w, xmax))
            if a1w > xmin:
                norm.append((xmin, a1w))
        else:
            left = max(a0w, xmin)
            right = min(a1w, xmax)
            if right > left:
                norm.append((left, right))
    return norm


def _draw_tdc_ut_markers(ax, xmin: float, xmax: float, cycle_deg: float):
    ref_angles = [(-360.0, "OT"), (-180.0, "UT"), (0.0, "OT"), (180.0, "UT"), (360.0, "OT")]
    trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    used = set()
    for ang, lab in ref_angles:
        if ang < xmin - 1e-9 or ang > xmax + 1e-9:
            continue
        key = (round(ang, 8), lab)
        if key in used:
            continue
        used.add(key)
        ax.axvline(ang, color="0.85", linewidth=0.45, zorder=0)
        ax.text(ang, -0.11, lab, transform=trans, ha="center", va="top", fontsize=EVENT_LABEL_FONT, clip_on=False)


def _t(ax, deg, r, s, **kwargs):
    ax.text(np.deg2rad(deg), r, s, ha=kwargs.pop("ha", "center"), va=kwargs.pop("va", "center"), **kwargs)


def _arc_segments(ax, a0, a1, r, cycle_deg=720.0, **kwargs):
    a0 = float(a0)
    a1 = float(a1)
    if a1 < a0:
        a1 += cycle_deg
    th = np.linspace(np.deg2rad(a0 % 360.0), np.deg2rad(a1 % 360.0) if (a1 % 360.0) >= (a0 % 360.0) else np.deg2rad(a1 % 360.0) + 2 * np.pi, 240)
    rr = np.full_like(th, r)
    ax.plot(th, rr, **kwargs)


def _overlap_segments_from_events(events):
    if not all(k in events for k in ("IVO_deg", "EVC_deg")):
        return []
    ivo = float(events["IVO_deg"])
    evc = float(events["EVC_deg"])
    if ivo < 360.0 and evc > 360.0:
        return [(ivo, evc)]
    if ivo > evc:
        return [(ivo, 360.0), (0.0, evc)]
    return []


def plot_steuerkreisdiagramm(
    events: dict,
    out_path: Path,
    cycle_deg: float = 720.0,
    overlap: dict | None = None,
):
    if abs(float(cycle_deg) - 720.0) > 1e-6:
        return None
    need = ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg")
    if not all(k in events for k in need):
        return None

    ivo = float(events["IVO_deg"])
    ivc = float(events["IVC_deg"])
    evo = float(events["EVO_deg"])
    evc = float(events["EVC_deg"])
    ivc_plot = ivc if ivc >= ivo else ivc + 720.0
    evc_plot = evc if evc >= evo else evc + 720.0

    fig = plt.figure(figsize=(6.1, 6.1))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 30), fontsize=TICK_FONT)
    ax.set_rticks([])
    ax.set_ylim(0, 1.18)
    ax.grid(True, linewidth=0.45, alpha=0.6)

    th = np.linspace(0, 2 * np.pi, 720)
    ax.plot(th, np.ones_like(th), linewidth=0.9, color="0.2")

    refs = [(0.0, "OT"), (180.0, "UT")]
    for ang, label in refs:
        a = np.deg2rad(ang)
        ax.plot([a, a], [0.0, 1.05], linestyle=":", linewidth=0.55, color="0.55")
        _t(ax, ang, 1.11, label, fontsize=POLAR_AXIS_FONT)
    _t(ax, 0.0, 0.12, "Overlap", fontsize=POLAR_TEXT_FONT)

    ov_segments = overlap.get("segments") if overlap else None
    if not ov_segments:
        ov_segments = _overlap_segments_from_events(events)
    for a0, a1 in ov_segments or []:
        if a1 < a0:
            a1 += 720.0
        cur = a0
        while cur < a1 - 1e-9:
            stop = min(a1, (math.floor(cur / 360.0) + 1.0) * 360.0)
            start_mod = cur % 360.0
            stop_mod = stop % 360.0
            if abs(stop_mod) < 1e-9 and stop > cur:
                th = np.linspace(np.deg2rad(start_mod), 2 * np.pi, 150)
            else:
                th = np.linspace(np.deg2rad(start_mod), np.deg2rad(stop_mod), 150)
            ax.fill_between(th, 0.92, 0.985, alpha=0.20, color=OVERLAP_COLOR, hatch="///", edgecolor="0.55", linewidth=0.0)
            cur = stop

    _arc_segments(ax, ivo, ivc_plot, 1.00, color="tab:blue", linewidth=2.0)
    _arc_segments(ax, evo, evc_plot, 0.88, color="tab:red", linewidth=2.0)

    polar_labels = [
        (ivo, "IVO", 1.05, "tab:blue", 0.05),
        (ivc, "IVC", 1.05, "tab:blue", 0.05),
        (evo, "EVO", 0.83, "tab:red", -0.06),
        (evc, "EVC", 0.83, "tab:red", -0.06),
    ]
    used_angles = []
    for ang, label, r, color, dr in polar_labels:
        ang_mod = ang % 360.0
        adjust = 0.0
        for prev in used_angles:
            if abs(((ang_mod - prev + 180.0) % 360.0) - 180.0) < 10.0:
                adjust = 0.05 if dr >= 0 else -0.05
        used_angles.append(ang_mod)
        a = np.deg2rad(ang_mod)
        ax.plot([a], [r], marker="o", color=color, markersize=3)
        _t(ax, ang_mod, r + dr + adjust, label, fontsize=POLAR_TEXT_FONT, color=color)

    fig.subplots_adjust(left=0.04, right=0.96, bottom=0.04, top=0.96)
    out_png = out_path.with_name(out_path.stem + "_steuerkreis.png")
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_png


def plot_steuerdiagramm(
    df,
    events: dict,
    out_path: Path,
    cycle_deg: float = 720.0,
    angle_ref_mode: str = "FIRE_TDC",
    overlap: dict | None = None,
    slot_events: dict | None = None,
    plot_theta_min_deg: float = -360.0,
    plot_theta_max_deg: float = 360.0,
):
    need = ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg")
    if df is None or not all(k in events for k in need):
        return None

    cycle_deg = float(cycle_deg)
    xmin = float(plot_theta_min_deg)
    xmax = float(plot_theta_max_deg)
    if xmax <= xmin:
        xmin, xmax = -0.5 * cycle_deg, 0.5 * cycle_deg

    fig = plt.figure(figsize=(8.2, 3.4))
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()

    ax.set_xlim(xmin, xmax)
    xtick_step = 60.0 if (xmax - xmin) <= 720.0 else 90.0
    ax.set_xticks(np.arange(math.ceil(xmin / xtick_step) * xtick_step, xmax + 1e-9, xtick_step))
    ax.tick_params(axis="both", labelsize=TICK_FONT)
    ax2.tick_params(axis="y", labelsize=TICK_FONT)
    ax.set_xlabel("Kurbelwinkel [°KW]", fontsize=AXIS_LABEL_FONT)
    ax.set_ylabel("Volumen [cm³]", fontsize=AXIS_LABEL_FONT)
    ax2.set_ylabel("Ventilhub [mm]", fontsize=AXIS_LABEL_FONT)
    ax.grid(True, linewidth=0.45, alpha=0.5)

    vol = _prepare_xy(df, "V_m3", xmin, xmax, cycle_deg)
    if vol is not None:
        x, y = vol
        ax.plot(x, y * 1.0e6, linestyle="--", color=VOLUME_COLOR, linewidth=0.9, zorder=2)

    lift_in = _prepare_xy(df, "lift_in_mm", xmin, xmax, cycle_deg)
    if lift_in is not None:
        ax2.plot(lift_in[0], lift_in[1], linewidth=0.9, label="Einlasshub", zorder=3)
    lift_ex = _prepare_xy(df, "lift_ex_mm", xmin, xmax, cycle_deg)
    if lift_ex is not None:
        ax2.plot(lift_ex[0], lift_ex[1], linewidth=0.9, label="Auslasshub", zorder=3)

    for a0, a1 in _normalize_segments(overlap.get("segments") if overlap else [], xmin, xmax, cycle_deg):
        ax.axvspan(a0, a1, alpha=0.12, color=OVERLAP_COLOR, zorder=0)

    for key in ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg"):
        if key in events:
            xx = _wrap_to_window(np.array([float(events[key])]), xmin, xmax, cycle_deg)[0]
            ax.axvline(xx, color=EVENT_COLOR, linestyle=":", linewidth=EVENT_LINEWIDTH, zorder=1)

    if slot_events:
        for key in ("INT_OPEN_deg", "INT_CLOSE_deg", "EXH_OPEN_deg", "EXH_CLOSE_deg"):
            if key in slot_events:
                xx = _wrap_to_window(np.array([float(slot_events[key])]), xmin, xmax, cycle_deg)[0]
                ax.axvline(xx, color="0.70", linestyle=":", linewidth=0.35, zorder=1)

    _draw_tdc_ut_markers(ax, xmin, xmax, cycle_deg)
    _add_phase_labels(ax, xmin, xmax, cycle_deg, angle_ref_mode)
    _draw_event_labels(ax, ax2, events, xmin, xmax, cycle_deg)

    info_lines = _format_event_lines(events, overlap=overlap, slot_events=slot_events)
    if info_lines:
        fig.text(0.82, 0.92, "\n".join(info_lines), ha="left", va="top", fontsize=SUMMARY_FONT)

    fig.subplots_adjust(left=0.09, right=0.79, bottom=0.31, top=0.93)
    out_png = out_path.with_name(out_path.stem + "_steuerzeiten.png")
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)

    plot_steuerkreisdiagramm(events, out_path, cycle_deg=cycle_deg, overlap=overlap)
    return out_png
