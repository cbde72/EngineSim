from __future__ import annotations

"""Spezialisierte Steuerzeiten- und Steuerkreis-Plots für MotorSim.

Dieses Modul erzeugt zwei eigenständige Ausgaben:

1. ``*_steuerzeiten.png``
   Kartesisches Diagramm mit Volumen und Ventilhub über dem Kurbelwinkel.
2. ``*_steuerkreis.png``
   Polarer Steuerkreis für eine kompakte klassische Darstellung der
   Einlass- und Auslassphasen.

Designziele
-----------
- kleine, dichte Engineering-Darstellung mit gut lesbarer Beschriftung
- robuste Darstellung für ein 720°-Arbeitsverfahren
- Kollisionsreduktion bei Event-Labels (IVO/IVC/EVO/EVC)
- OT/UT-Markierungen und optionale Overlap-Hervorhebung

Hinweise zur Datenbasis
-----------------------
Erwartete DataFrame-Spalten für ``plot_steuerdiagramm``:
- ``theta_deg``
- ``V_m3``
- optional ``lift_in_mm``
- optional ``lift_ex_mm``

Erwartete Event-Keys:
- ``IVO_deg``, ``IVC_deg``, ``EVO_deg``, ``EVC_deg``

Das Modul ist bewusst weitgehend zustandslos gehalten. Alle Helper-Funktionen
arbeiten rein funktional auf NumPy-Arrays oder Dictionaries.
"""

from pathlib import Path
from datetime import datetime
import math
from typing import Iterable

import matplotlib.pyplot as plt
from matplotlib import transforms
import numpy as np

# -----------------------------------------------------------------------------
# Plot-Layout-Konstanten
# -----------------------------------------------------------------------------
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
DPI = 120

INFO_BOX_POSITIONS = {
    'upper right': (0.82, 0.92, 'left', 'top'),
    'upper left': (0.03, 0.92, 'left', 'top'),
    'lower right': (0.82, 0.08, 'left', 'bottom'),
    'lower left': (0.03, 0.08, 'left', 'bottom'),
    'outside right upper': (0.82, 0.92, 'left', 'top'),
    'outside right lower': (0.82, 0.10, 'left', 'bottom'),
}

def _style_value(style: dict | None, group: str, key: str, default):
    if not style:
        return default
    return style.get(group, {}).get(key, default)


# -----------------------------------------------------------------------------
# Basis-Helfer
# -----------------------------------------------------------------------------
def _phase_segments(cycle_deg: float, angle_ref_mode: str) -> list[tuple[float, float, str]]:
    """Liefert die Phasenbeschriftung für einen 720°-Prozess.

    Parameters
    ----------
    cycle_deg:
        Arbeitszyklus in Kurbelgrad. Nur 720° wird aktuell unterstützt.
    angle_ref_mode:
        Referenzmodus des Winkelursprungs, z. B. ``FIRE_TDC`` oder
        ``GAS_EXCHANGE_TDC``.

    Returns
    -------
    list[tuple[float, float, str]]
        Liste aus ``(start_deg, end_deg, label)``.
    """
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

    # Standard: FIRE_TDC
    return [
        (-360.0, -180.0, "Arbeiten"),
        (-180.0, 0.0, "Ausschieben"),
        (0.0, 180.0, "Ansaugen"),
        (180.0, 360.0, "Verdichten"),
    ]


def _wrap_to_window(theta_deg: np.ndarray, xmin: float, xmax: float, cycle_deg: float) -> np.ndarray:
    """Verschiebt Winkel in das sichtbare Plotfenster.

    Die Funktion faltet absolute Kurbelwinkel so um, dass sie möglichst nahe um
    das Fensterzentrum liegen. Dadurch können Signale in Fenstern wie
    ``[-360, 360]`` oder ``[0, 720]`` konsistent visualisiert werden.
    """
    center = 0.5 * (xmin + xmax)
    return ((theta_deg - center + 0.5 * cycle_deg) % cycle_deg) - 0.5 * cycle_deg + center


def _prepare_xy(df, column: str, xmin: float, xmax: float, cycle_deg: float) -> tuple[np.ndarray, np.ndarray] | None:
    """Bereitet X/Y-Daten einer Spalte für einen winkelbasierten Plot auf.

    Schritte:
    1. Existenzprüfung der Spalte
    2. Finite Werte filtern
    3. Winkel in das Sichtfenster umlegen
    4. Sortieren
    5. doppelte X-Werte entfernen
    """
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


# -----------------------------------------------------------------------------
# Beschriftungen und Annotationen
# -----------------------------------------------------------------------------
def _add_phase_labels(ax, xmin: float, xmax: float, cycle_deg: float, angle_ref_mode: str, phase_font: float = PHASE_FONT) -> None:
    """Schreibt die Prozessphasen unter die x-Achse."""
    segments = _phase_segments(cycle_deg, angle_ref_mode)
    if not segments:
        return

    trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for a0, a1, label in segments:
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
    """Erzeugt den rechten Zusammenfassungsblock des Steuerzeitenplots."""
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
    """Normalisiert Event-Winkel in das Plotfenster und sortiert sie."""
    items: list[tuple[float, str, float]] = []
    for key, label in (("IVO_deg", "IVO"), ("IVC_deg", "IVC"), ("EVO_deg", "EVO"), ("EVC_deg", "EVC")):
        if key in events:
            wrapped_x = _wrap_to_window(np.array([float(events[key])]), xmin, xmax, cycle_deg)[0]
            items.append((wrapped_x, label, float(events[key])))
    return sorted(items, key=lambda item: item[0])


def _draw_event_labels(ax, ax2, events: dict, xmin: float, xmax: float, cycle_deg: float, event_label_font: float = EVENT_LABEL_FONT, event_color: str = EVENT_COLOR) -> None:
    """Zeichnet Event-Labels oberhalb des Hubsignals mit einfacher Kollisionsreduktion.

    Strategie
    ---------
    - Events werden nach x sortiert.
    - Liegen zwei Events zu nah zusammen, wird ein höheres y-Level verwendet.
    - Die Sekundärachse wird nach oben erweitert, damit Labels und Pfeile nicht
      abgeschnitten werden.

    Das Verfahren ist bewusst leichtgewichtig. Es ist deterministisch und erzeugt
    keine externen Abhängigkeiten.
    """
    items = _event_positions(events, xmin, xmax, cycle_deg)
    if not items:
        return

    y0, y1 = ax2.get_ylim()
    y_range = max(y1 - y0, 1.0)
    base = y1 + 0.06 * y_range

    # Minimaler x-Abstand in Plotkoordinaten, unterhalb dessen gestapelt wird.
    min_dx = max((xmax - xmin) * 0.055, 18.0)
    levels = [0.0, 0.09 * y_range, 0.18 * y_range, 0.27 * y_range]

    label_pos: list[tuple[float, float, str]] = []
    placed_x: list[float] = []

    for x, label, _raw in items:
        level_idx = 0
        if placed_x and abs(x - placed_x[-1]) < min_dx:
            level_idx = min(len(placed_x), len(levels) - 1)
        y = base + levels[level_idx]
        label_pos.append((x, y, label))
        placed_x.append(x)

    ax2.set_ylim(y0, max(y1, base + max(levels) + 0.08 * y_range))
    y_top = y0 + 0.985 * (ax2.get_ylim()[1] - y0)

    for x, y, label in label_pos:
        ax2.annotate(
            label,
            xy=(x, y_top),
            xytext=(x, y),
            textcoords="data",
            ha="center",
            va="bottom",
            fontsize=EVENT_LABEL_FONT,
            color=event_color,
            arrowprops=dict(arrowstyle="-", color=EVENT_COLOR, lw=0.35, shrinkA=0, shrinkB=0),
            clip_on=False,
        )


# -----------------------------------------------------------------------------
# Segment- und Marker-Helfer
# -----------------------------------------------------------------------------
def _normalize_segments(segments: Iterable[tuple[float, float]] | None, xmin: float, xmax: float, cycle_deg: float) -> list[tuple[float, float]]:
    """Projiziert Segmente in das aktive Sichtfenster.

    Wichtig für Overlap-Segmente, die ggf. über den Fensterrand oder über den
    0/720°-Sprung laufen.
    """
    normalized: list[tuple[float, float]] = []
    for a0, a1 in segments or []:
        a0w = _wrap_to_window(np.array([float(a0)]), xmin, xmax, cycle_deg)[0]
        a1w = _wrap_to_window(np.array([float(a1)]), xmin, xmax, cycle_deg)[0]

        if a1w < a0w:
            if xmax > a0w:
                normalized.append((a0w, xmax))
            if a1w > xmin:
                normalized.append((xmin, a1w))
        else:
            left = max(a0w, xmin)
            right = min(a1w, xmax)
            if right > left:
                normalized.append((left, right))

    return normalized


def _draw_tdc_ut_markers(ax, xmin: float, xmax: float, cycle_deg: float) -> None:
    """Zeichnet OT-/UT-Referenzen für den 720°-Plotbereich."""
    ref_angles = [(-360.0, "OT"), (-180.0, "UT"), (0.0, "OT"), (180.0, "UT"), (360.0, "OT")]
    trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    used = set()

    for angle_deg, label in ref_angles:
        if angle_deg < xmin - 1e-9 or angle_deg > xmax + 1e-9:
            continue

        key = (round(angle_deg, 8), label)
        if key in used:
            continue
        used.add(key)

        ax.axvline(angle_deg, color="0.85", linewidth=0.45, zorder=0)
        ax.text(angle_deg, -0.11, label, transform=trans, ha="center", va="top", fontsize=EVENT_LABEL_FONT, clip_on=False)


def _polar_text(ax, deg: float, radius: float, text: str, **kwargs) -> None:
    """Komfort-Wrapper für Polarkoordinaten-Text."""
    ax.text(np.deg2rad(deg), radius, text, ha=kwargs.pop("ha", "center"), va=kwargs.pop("va", "center"), **kwargs)


def _arc_segments(ax, a0: float, a1: float, radius: float, cycle_deg: float = 720.0, **kwargs) -> None:
    """Zeichnet einen Winkelbogen in der Polardarstellung."""
    a0 = float(a0)
    a1 = float(a1)
    if a1 < a0:
        a1 += cycle_deg

    start = np.deg2rad(a0 % 360.0)
    stop_mod = a1 % 360.0
    stop = np.deg2rad(stop_mod) if stop_mod >= (a0 % 360.0) else np.deg2rad(stop_mod) + 2.0 * np.pi
    theta = np.linspace(start, stop, 240)
    radius_arr = np.full_like(theta, radius)
    ax.plot(theta, radius_arr, **kwargs)


def _overlap_segments_from_events(events: dict) -> list[tuple[float, float]]:
    """Leitet Overlap grob aus IVO und EVC ab, falls kein Overlap-Objekt vorliegt."""
    if not all(key in events for key in ("IVO_deg", "EVC_deg")):
        return []

    ivo = float(events["IVO_deg"])
    evc = float(events["EVC_deg"])

    if ivo < 360.0 and evc > 360.0:
        return [(ivo, evc)]
    if ivo > evc:
        return [(ivo, 360.0), (0.0, evc)]
    return []


def _save_with_optional_timestamp(fig, out_png: Path, dpi: int, auto_save: bool = False, timestamp_dir: str = 'timestamped_plots') -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    if auto_save:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_dir = out_png.parent / timestamp_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        stamped = target_dir / f'{out_png.stem}_{ts}{out_png.suffix}'
        fig.savefig(stamped, dpi=dpi, bbox_inches="tight")


def _timing_cfg(style: dict | None, key: str) -> dict:
    if not style:
        return {}
    return dict((style.get('timing_plots', {}) or {}).get(key, {}) or {})


# -----------------------------------------------------------------------------
# Öffentliche Plotfunktionen
# -----------------------------------------------------------------------------
def plot_steuerkreisdiagramm(
    events: dict,
    out_path: Path,
    cycle_deg: float = 720.0,
    overlap: dict | None = None,
    style: dict | None = None,
    crank_angle_offset_deg: float = 0.0,
):
    """Erzeugt das polare Steuerkreisdiagramm."""
    del crank_angle_offset_deg
    if abs(float(cycle_deg) - 720.0) > 1e-6:
        return None

    required = ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg")
    if not all(key in events for key in required):
        return None

    polar_cfg = _timing_cfg(style, 'polar')

    ivo = float(events["IVO_deg"])
    ivc = float(events["IVC_deg"])
    evo = float(events["EVO_deg"])
    evc = float(events["EVC_deg"])

    ivc_plot = ivc if ivc >= ivo else ivc + 720.0
    evc_plot = evc if evc >= evo else evc + 720.0

    figsize = polar_cfg.get('figsize_in', [6.1, 6.1])
    fig = plt.figure(figsize=(float(figsize[0]), float(figsize[1])))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 30), fontsize=TICK_FONT)
    ax.set_rticks([])
    ax.set_ylim(0, 1.18)
    ax.grid(True, linewidth=0.45, alpha=0.6)

    theta_circle = np.linspace(0.0, 2.0 * np.pi, 720)
    ax.plot(theta_circle, np.ones_like(theta_circle), linewidth=0.9, color="0.2")

    for angle_deg, label in ((0.0, "OT"), (180.0, "UT")):
        angle_rad = np.deg2rad(angle_deg)
        ax.plot([angle_rad, angle_rad], [0.0, 1.05], linestyle=":", linewidth=0.55, color="0.55")
        _polar_text(ax, angle_deg, 1.11, label, fontsize=POLAR_AXIS_FONT)

    _polar_text(ax, 0.0, 0.12, "Overlap", fontsize=POLAR_TEXT_FONT)

    overlap_segments = overlap.get("segments") if overlap else None
    if not overlap_segments:
        overlap_segments = _overlap_segments_from_events(events)

    for a0, a1 in overlap_segments or []:
        if a1 < a0:
            a1 += 720.0
        current = a0
        while current < a1 - 1e-9:
            stop = min(a1, (math.floor(current / 360.0) + 1.0) * 360.0)
            start_mod = current % 360.0
            stop_mod = stop % 360.0
            if abs(stop_mod) < 1e-9 and stop > current:
                theta = np.linspace(np.deg2rad(start_mod), 2.0 * np.pi, 150)
            else:
                theta = np.linspace(np.deg2rad(start_mod), np.deg2rad(stop_mod), 150)
            ax.fill_between(theta, 0.92, 0.985, alpha=0.20, color=OVERLAP_COLOR, hatch="///", edgecolor="0.55", linewidth=0.0)
            current = stop

    _arc_segments(ax, ivo, ivc_plot, 1.00, color="tab:blue", linewidth=2.0)
    _arc_segments(ax, evo, evc_plot, 0.88, color="tab:red", linewidth=2.0)

    polar_labels = [
        (ivo, "IVO", 1.05, "tab:blue", 0.05),
        (ivc, "IVC", 1.05, "tab:blue", 0.05),
        (evo, "EVO", 0.83, "tab:red", -0.06),
        (evc, "EVC", 0.83, "tab:red", -0.06),
    ]

    used_angles: list[float] = []
    for angle_deg, label, radius, color, dr in polar_labels:
        angle_mod = angle_deg % 360.0
        adjust = 0.0
        for prev in used_angles:
            if abs(((angle_mod - prev + 180.0) % 360.0) - 180.0) < 10.0:
                adjust = 0.05 if dr >= 0 else -0.05
        used_angles.append(angle_mod)
        angle_rad = np.deg2rad(angle_mod)
        ax.plot([angle_rad], [radius], marker="o", color=color, markersize=3)
        _polar_text(ax, angle_mod, radius + dr + adjust, label, fontsize=POLAR_TEXT_FONT, color=color)

    fig.subplots_adjust(left=0.04, right=0.96, bottom=0.04, top=0.96)
    out_png = out_path.with_name(out_path.stem + "_steuerkreis.png")
    _save_with_optional_timestamp(
        fig,
        out_png,
        dpi=int(polar_cfg.get('dpi', DPI)),
        auto_save=bool(polar_cfg.get('auto_save_timestamped', False)),
        timestamp_dir=str(polar_cfg.get('timestamp_dir', 'timestamped_plots')),
    )
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
    style: dict | None = None,
    crank_angle_offset_deg: float = 0.0,
):
    """Erzeugt das kartesische Steuerzeiten-Diagramm."""
    del crank_angle_offset_deg
    required = ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg")
    if df is None or not all(key in events for key in required):
        return None

    cycle_deg = float(cycle_deg)
    xmin = float(plot_theta_min_deg)
    xmax = float(plot_theta_max_deg)
    if xmax <= xmin:
        xmin, xmax = -0.5 * cycle_deg, 0.5 * cycle_deg

    cart_cfg = _timing_cfg(style, 'cartesian')
    if not bool(cart_cfg.get('enabled', True)):
        if bool(_timing_cfg(style, 'polar').get('enabled', True)):
            return plot_steuerkreisdiagramm(events, out_path, cycle_deg=cycle_deg, overlap=overlap, style=style)
        return None

    figsize = cart_cfg.get('figsize_in', [8.2, 3.4])
    fig = plt.figure(figsize=(float(figsize[0]), float(figsize[1])))
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()

    ax.set_xlim(xmin, xmax)
    xtick_step = float(cart_cfg.get('xtick_step_deg', 60.0 if (xmax - xmin) <= 720.0 else 90.0))
    ax.set_xticks(np.arange(math.ceil(xmin / xtick_step) * xtick_step, xmax + 1e-9, xtick_step))
    ax.tick_params(axis="both", labelsize=TICK_FONT)
    ax2.tick_params(axis="y", labelsize=TICK_FONT)
    ax.set_xlabel(str(cart_cfg.get('xlabel', 'Kurbelwinkel [°KW]')), fontsize=AXIS_LABEL_FONT)
    ax.set_ylabel(str(cart_cfg.get('ylabel', 'Volumen [cm³]')), fontsize=AXIS_LABEL_FONT)
    ax2.set_ylabel(str(cart_cfg.get('y2label', 'Ventilhub [mm]')), fontsize=AXIS_LABEL_FONT)
    ax.grid(bool(cart_cfg.get('grid', True)), linewidth=0.45, alpha=0.5)

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
    _add_phase_labels(ax, xmin, xmax, cycle_deg, angle_ref_mode, phase_font=PHASE_FONT)
    _draw_event_labels(ax, ax2, events, xmin, xmax, cycle_deg, event_label_font=EVENT_LABEL_FONT, event_color=EVENT_COLOR)

    info_lines = _format_event_lines(events, overlap=overlap, slot_events=slot_events)
    if info_lines:
        x, y, ha, va = INFO_BOX_POSITIONS.get(str(cart_cfg.get('info_box_loc', 'outside right upper')), INFO_BOX_POSITIONS['outside right upper'])
        fig.text(x, y, "\n".join(info_lines), ha=ha, va=va, fontsize=SUMMARY_FONT)

    fig.subplots_adjust(left=0.09, right=0.79, bottom=0.31, top=0.93)
    out_png = out_path.with_name(out_path.stem + "_steuerzeiten.png")
    _save_with_optional_timestamp(
        fig,
        out_png,
        dpi=int(cart_cfg.get('dpi', DPI)),
        auto_save=bool(cart_cfg.get('auto_save_timestamped', False)),
        timestamp_dir=str(cart_cfg.get('timestamp_dir', 'timestamped_plots')),
    )
    plt.close(fig)

    if bool(_timing_cfg(style, 'polar').get('enabled', True)):
        plot_steuerkreisdiagramm(events, out_path, cycle_deg=cycle_deg, overlap=overlap, style=style)
    return out_png
