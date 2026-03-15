from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from .phase_logic import reference_points

PHASE_COLORS = {
    'ansaugen': 0.96,
    'verdichten': 0.92,
    'arbeiten': 0.88,
    'ausschieben': 0.84,
}

SERIES_ALIASES = {
    'p_cyl_bar': ('p_cyl_pa', 1e-5),
    'p_ref_compression_bar': ('p_ref_compression_pa', 1e-5),
    'p_ref_expansion_bar': ('p_ref_expansion_pa', 1e-5),
    'V_cm3': ('V_m3', 1e6),
    'A_in_mm2': ('A_in_m2', 1e6),
    'A_ex_mm2': ('A_ex_m2', 1e6),
}

DEFAULT_STYLE = {
    'figures': [
        {
            'name': 'Hauptlayout',
            'file_suffix': '',
            'figsize_in': [13, 12],
            'dpi': 180,
            'title': 'MotorSim – gespeicherte Zyklen',
            'title_fontsize': 12,
            'label_fontsize': 10,
            'tick_labelsize': 9,
            'legend_fontsize': 8,
            'info_fontsize': 8,
            'reference_label_fontsize': 8,
            'reference_linewidth': 0.8,
            'line_width': 1.5,
            'rows': 5,
            'cols': 1,
            'sharex': True,
            'xlabel': 'Kurbelwinkel [deg KW]',
            'spacing': {'left': 0.08, 'right': 0.95, 'bottom': 0.06, 'top': 0.95, 'hspace': 0.18, 'wspace': 0.12},
            'xtick_step_deg': 180.0,
            'show_info_box': True,
            'info_box_loc': 'upper right',
            'auto_save_timestamped': False,
            'timestamp_dir': 'timestamped_plots',
            'plots': [
                {
                    'title': 'Druck',
                    'ylabel': 'p [bar]',
                    'legend_loc': 'upper right',
                    'shade_phases': True,
                    'reference_lines': True,
                    'grid': True,
                    'series': [
                        {'key': 'p_cyl_bar', 'label': 'p_cyl', 'color': 'tab:blue', 'linewidth': 1.8},
                        {'key': 'p_ref_compression_bar', 'label': 'p_ref Verdichtung', 'linestyle': '--', 'color': 'tab:orange'},
                        {'key': 'p_ref_expansion_bar', 'label': 'p_ref Expansion', 'linestyle': ':', 'color': 'tab:green'},
                    ],
                },
                {
                    'title': 'Volumen und Ventilhub',
                    'ylabel': 'V [cm³]',
                    'y2label': 'Ventilhub [mm]',
                    'legend_loc': 'upper right',
                    'shade_phases': True,
                    'reference_lines': True,
                    'grid': True,
                    'series': [{'key': 'V_cm3', 'label': 'V', 'linestyle': '--', 'color': 'tab:purple'}],
                    'secondary_series': [
                        {'key': 'lift_in_mm', 'label': 'Hub Einlass', 'color': 'tab:red'},
                        {'key': 'lift_ex_mm', 'label': 'Hub Auslass', 'color': 'tab:brown'},
                    ],
                },
                {
                    'title': 'Massenstrom',
                    'ylabel': 'ṁ [kg/s]',
                    'legend_loc': 'upper right',
                    'shade_phases': True,
                    'reference_lines': True,
                    'grid': True,
                    'series': [
                        {'key': 'mdot_in_kg_s', 'label': 'ṁ Einlass', 'color': 'tab:blue'},
                        {'key': 'mdot_out_kg_s', 'label': 'ṁ Auslass', 'color': 'tab:orange'},
                    ],
                },
                {
                    'title': 'alphaK / Aeff',
                    'ylabel': 'alphaK / alphaV [-]',
                    'y2label': 'A_eff [mm²]',
                    'legend_loc': 'upper right',
                    'shade_phases': True,
                    'reference_lines': True,
                    'grid': True,
                    'series': [
                        {'key': 'alphaK_in', 'label': 'alphaK Einströmen', 'color': 'tab:blue'},
                        {'key': 'alphaK_ex', 'label': 'alphaK Ausströmen', 'color': 'tab:orange'},
                        {'key': 'alphaV_in', 'label': 'alphaV Einströmen', 'linestyle': '--', 'color': 'tab:green'},
                        {'key': 'alphaV_ex', 'label': 'alphaV Ausströmen', 'linestyle': ':', 'color': 'tab:red'},
                    ],
                    'secondary_series': [
                        {'key': 'A_in_mm2', 'label': 'A_eff Einlass', 'linestyle': '--', 'color': 'tab:purple'},
                        {'key': 'A_ex_mm2', 'label': 'A_eff Auslass', 'linestyle': ':', 'color': 'tab:brown'},
                    ],
                },
                {
                    'title': 'Wärmezufuhr / Burn Fraction',
                    'ylabel': 'Q̇ [W]',
                    'y2label': 'x_b [-]',
                    'legend_loc': 'upper right',
                    'shade_phases': True,
                    'reference_lines': True,
                    'grid': True,
                    'series': [{'key': 'qdot_combustion_W', 'label': 'Q̇_comb', 'color': 'tab:blue'}],
                    'secondary_series': [{'key': 'xb_combustion', 'label': 'x_b', 'linestyle': '--', 'color': 'tab:orange'}],
                },
            ],
            'pv_plot': {
                'enabled': True,
                'figsize_in': [7, 6],
                'xlabel': 'V [m³]',
                'ylabel': 'p [Pa]',
                'title': 'p-V Diagramm',
                'grid': True,
                'legend_loc': 'best',
                'series': [{'x_key': 'V_m3', 'y_key': 'p_cyl_pa', 'label': 'p-V', 'color': 'tab:blue'}],
            },
        }
    ],
    'timing_plots': {
        'cartesian': {
            'enabled': True,
            'info_box_loc': 'outside right upper',
            'auto_save_timestamped': False,
            'timestamp_dir': 'timestamped_plots',
        },
        'polar': {
            'enabled': True,
            'auto_save_timestamped': False,
            'timestamp_dir': 'timestamped_plots',
        },
    },
}


INFO_BOX_POSITIONS = {
    'upper right': (0.995, 0.98, 'right', 'top'),
    'upper left': (0.005, 0.98, 'left', 'top'),
    'lower right': (0.995, 0.02, 'right', 'bottom'),
    'lower left': (0.005, 0.02, 'left', 'bottom'),
    'outside right upper': (1.02, 0.98, 'left', 'top'),
    'outside right lower': (1.02, 0.02, 'left', 'bottom'),
}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_style(style: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_STYLE, style or {})
    if 'figures' not in merged:
        if 'main_plot' in merged:
            main_plot = merged.pop('main_plot')
            merged['figures'] = [main_plot]
        else:
            merged['figures'] = list(DEFAULT_STYLE['figures'])
    return merged


def _phase_segments(theta: np.ndarray, phases: np.ndarray):
    if len(theta) == 0:
        return []
    segs = []
    start = 0
    for i in range(1, len(theta)):
        if phases[i] != phases[start]:
            segs.append((float(theta[start]), float(theta[i - 1]), str(phases[start])))
            start = i
    segs.append((float(theta[start]), float(theta[-1]), str(phases[start])))
    return segs


def _shade_phases(ax, theta, phases):
    for a, b, ph in _phase_segments(theta, phases):
        alpha = PHASE_COLORS.get(ph, 0.97)
        ax.axvspan(a, b, color=str(alpha), zorder=0)


def _add_reference_lines(ax, refs: dict, theta_min: float, theta_max: float, cycle_deg: float, ref_label_fontsize: float = 8.0, ref_linewidth: float = 0.8):
    y0, _ = ax.get_ylim()
    start_k = int(np.floor(theta_min / cycle_deg)) - 1
    end_k = int(np.ceil(theta_max / cycle_deg)) + 1
    labels = [
        ('firing_tdc_deg', 'Zünd-OT'),
        ('power_bdc_deg', 'Arbeits-UT'),
        ('gas_exchange_tdc_deg', 'Gaswechsel-OT'),
        ('intake_bdc_deg', 'Ansaug-UT'),
    ]
    for k in range(start_k, end_k + 1):
        base = k * cycle_deg
        for key, label in labels:
            x = base + float(refs[key])
            if theta_min - 1e-9 <= x <= theta_max + 1e-9:
                ax.axvline(x, linestyle='--', linewidth=ref_linewidth, color='0.45')
                ax.text(x, y0, label, rotation=90, va='bottom', ha='right', fontsize=ref_label_fontsize)


def _resolve_series(df, key: str):
    if not key:
        return None
    if key in df.columns:
        return df[key].to_numpy(dtype=float)
    alias = SERIES_ALIASES.get(key)
    if alias and alias[0] in df.columns:
        return df[alias[0]].to_numpy(dtype=float) * float(alias[1])
    return None


def _scaled_series(df, item: dict[str, Any]):
    arr = _resolve_series(df, str(item.get('key', '')))
    if arr is None:
        return None
    scale = float(item.get('scale', 1.0) or 1.0)
    offset = float(item.get('offset', 0.0) or 0.0)
    return arr * scale + offset


def _plot_series_list(ax, x, df, items, default_linewidth: float):
    for item in items or []:
        arr = _scaled_series(df, item)
        if arr is None:
            continue
        ax.plot(
            x,
            arr,
            label=item.get('label') or item.get('key'),
            color=item.get('color'),
            linestyle=item.get('linestyle', '-'),
            linewidth=float(item.get('linewidth', default_linewidth)),
            alpha=float(item.get('alpha', 1.0)),
        )


def _info_lines(df, valve_events, timing_validation, closed_cycle_summary):
    lines = []
    if valve_events:
        for key in ('IVO_deg', 'IVC_deg', 'EVO_deg', 'EVC_deg'):
            if valve_events.get(key) is not None:
                lines.append(f"{key.replace('_deg', '')}: {float(valve_events[key]):.2f}°")
    if timing_validation:
        lines.append(f"Timing plausible: {timing_validation.get('timing_plausible')}")
    if closed_cycle_summary:
        ncomp = closed_cycle_summary.get('compression', {}).get('n_polytropic')
        nexp = closed_cycle_summary.get('expansion', {}).get('n_polytropic')
        if ncomp is not None:
            lines.append(f'n_verd: {float(ncomp):.4f}')
        if nexp is not None:
            lines.append(f'n_exp: {float(nexp):.4f}')
    if 'qdot_combustion_W' in df.columns and len(df):
        q = df['qdot_combustion_W'].to_numpy(dtype=float)
        if np.nanmax(np.abs(q)) > 0.0:
            lines.append(f'Q̇_comb,max: {float(np.nanmax(q)):.0f} W')
    if 'cycle_index' in df.columns and len(df):
        lines.append(f"Stored cycles: {int(df['cycle_index'].min())}..{int(df['cycle_index'].max())}")
    return lines


def _apply_info_box(ax, lines: list[str], loc: str, fontsize: float):
    if not lines:
        return
    x, y, ha, va = INFO_BOX_POSITIONS.get(loc, INFO_BOX_POSITIONS['upper right'])
    ax.text(x, y, '\n'.join(lines), transform=ax.transAxes, ha=ha, va=va, fontsize=fontsize)


def _save_figure(fig, path: Path, dpi: int | float, bbox_inches='tight', auto_save: bool = False, timestamp_dir: str = 'timestamped_plots'):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches=bbox_inches)
    if auto_save:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_dir = path.parent / timestamp_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        stamped = out_dir / f'{path.stem}_{ts}{path.suffix}'
        fig.savefig(stamped, dpi=dpi, bbox_inches=bbox_inches)


def create_layout_figure(
    df,
    fig_cfg: dict[str, Any],
    cycle_deg: float,
    angle_ref_mode: str,
    valve_events: dict | None = None,
    timing_validation: dict | None = None,
    closed_cycle_summary: dict | None = None,
    crank_angle_offset_deg: float = 0.0,
):
    theta = df['theta_deg'].to_numpy(dtype=float)
    theta_min = float(theta.min()) if len(theta) else 0.0
    theta_max = float(theta.max()) if len(theta) else float(cycle_deg)
    phases = df['ideal_phase'].to_numpy(dtype=object) if 'ideal_phase' in df.columns else None
    refs = reference_points(cycle_deg=cycle_deg, angle_ref_mode=angle_ref_mode, crank_angle_offset_deg=crank_angle_offset_deg)

    rows = max(1, int(fig_cfg.get('rows', 1)))
    cols = max(1, int(fig_cfg.get('cols', 1)))
    figsize = tuple(fig_cfg.get('figsize_in', [13, 12]))
    dpi = int(fig_cfg.get('dpi', 180))
    fig = plt.figure(figsize=figsize)
    axes = np.atleast_1d(fig.subplots(rows, cols, sharex=bool(fig_cfg.get('sharex', True)), squeeze=False)).flatten()

    plots_cfg = list(fig_cfg.get('plots', []))
    label_fontsize = float(fig_cfg.get('label_fontsize', 10))
    tick_labelsize = float(fig_cfg.get('tick_labelsize', 9))
    legend_fontsize = float(fig_cfg.get('legend_fontsize', 8))
    info_fontsize = float(fig_cfg.get('info_fontsize', 8))
    ref_label_fontsize = float(fig_cfg.get('reference_label_fontsize', 8))
    ref_linewidth = float(fig_cfg.get('reference_linewidth', 0.8))
    default_linewidth = float(fig_cfg.get('line_width', 1.5))

    for idx, ax in enumerate(axes):
        if idx >= len(plots_cfg):
            ax.axis('off')
            continue
        pcfg = plots_cfg[idx]
        if phases is not None and bool(pcfg.get('shade_phases', False)):
            _shade_phases(ax, theta, phases)
        _plot_series_list(ax, theta, df, pcfg.get('series', []), default_linewidth)
        ax.set_title(str(pcfg.get('title', '')), fontsize=float(pcfg.get('title_fontsize', label_fontsize)))
        ax.set_ylabel(str(pcfg.get('ylabel', '')), fontsize=label_fontsize)
        ax.grid(bool(pcfg.get('grid', True)))
        ax.tick_params(axis='both', labelsize=tick_labelsize)

        if bool(pcfg.get('reference_lines', False)):
            _add_reference_lines(ax, refs, theta_min, theta_max, cycle_deg, ref_label_fontsize=ref_label_fontsize, ref_linewidth=ref_linewidth)

        secondary = list(pcfg.get('secondary_series', []))
        if secondary:
            ax2 = ax.twinx()
            _plot_series_list(ax2, theta, df, secondary, default_linewidth)
            ax2.set_ylabel(str(pcfg.get('y2label', '')), fontsize=label_fontsize)
            ax2.tick_params(axis='y', labelsize=tick_labelsize)
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            if h1 or h2:
                ax2.legend(h1 + h2, l1 + l2, loc=pcfg.get('legend_loc', 'best'), fontsize=legend_fontsize)
        else:
            h, _ = ax.get_legend_handles_labels()
            if h:
                ax.legend(loc=pcfg.get('legend_loc', 'best'), fontsize=legend_fontsize)

        ax.set_xlim(theta_min, theta_max)
        step = float(fig_cfg.get('xtick_step_deg', 180.0))
        xt0 = step * np.floor(theta_min / step)
        ax.set_xticks(np.arange(xt0, theta_max + step + 1e-9, step))

    visible_axes = [ax for ax in axes if ax.axison]
    if visible_axes:
        visible_axes[-1].set_xlabel(str(fig_cfg.get('xlabel', 'Kurbelwinkel [deg KW]')), fontsize=label_fontsize)
        if bool(fig_cfg.get('show_info_box', True)):
            lines = _info_lines(df, valve_events, timing_validation, closed_cycle_summary)
            _apply_info_box(visible_axes[0], lines, str(fig_cfg.get('info_box_loc', 'upper right')), info_fontsize)

    spacing = fig_cfg.get('spacing', {}) or {}
    fig.subplots_adjust(
        left=float(spacing.get('left', 0.08)),
        right=float(spacing.get('right', 0.95)),
        bottom=float(spacing.get('bottom', 0.06)),
        top=float(spacing.get('top', 0.95)),
        hspace=float(spacing.get('hspace', 0.18)),
        wspace=float(spacing.get('wspace', 0.12)),
    )
    fig.suptitle(str(fig_cfg.get('title', '')), fontsize=float(fig_cfg.get('title_fontsize', 12)))

    return fig


def create_pv_figure(df, fig_cfg: dict[str, Any]):
    pv_plot = fig_cfg.get('pv_plot', {}) or {}
    if not bool(pv_plot.get('enabled', False)):
        return None
    dpi = int(pv_plot.get('dpi', fig_cfg.get('dpi', 180)))
    default_linewidth = float(fig_cfg.get('line_width', 1.5))
    pv_fig = plt.figure(figsize=tuple(pv_plot.get('figsize_in', [7, 6])), dpi=dpi)
    ax = pv_fig.add_subplot(111)
    for item in pv_plot.get('series', []) or []:
        x = _resolve_series(df, str(item.get('x_key', '')))
        y = _resolve_series(df, str(item.get('y_key', '')))
        if x is None or y is None:
            continue
        ax.plot(
            x,
            y,
            label=item.get('label') or f"{item.get('y_key')}({item.get('x_key')})",
            color=item.get('color'),
            linestyle=item.get('linestyle', '-'),
            linewidth=float(item.get('linewidth', default_linewidth)),
        )
    ax.set_xlabel(str(pv_plot.get('xlabel', 'V [m³]')))
    ax.set_ylabel(str(pv_plot.get('ylabel', 'p [Pa]')))
    ax.set_title(str(pv_plot.get('title', 'p-V Diagramm')))
    ax.grid(bool(pv_plot.get('grid', True)))
    handles, _ = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc=pv_plot.get('legend_loc', 'best'))
    return pv_fig


def _plot_one_layout(
    df,
    out_path: Path,
    fig_cfg: dict[str, Any],
    cycle_deg: float,
    angle_ref_mode: str,
    valve_events: dict | None,
    timing_validation: dict | None,
    closed_cycle_summary: dict | None,
    crank_angle_offset_deg: float,
):
    fig = create_layout_figure(
        df=df,
        fig_cfg=fig_cfg,
        cycle_deg=cycle_deg,
        angle_ref_mode=angle_ref_mode,
        valve_events=valve_events,
        timing_validation=timing_validation,
        closed_cycle_summary=closed_cycle_summary,
        crank_angle_offset_deg=crank_angle_offset_deg,
    )
    dpi = int(fig_cfg.get('dpi', 180))
    suffix = str(fig_cfg.get('file_suffix', '') or '')
    if suffix and not suffix.startswith('_'):
        suffix = '_' + suffix
    target = out_path.with_name(out_path.stem + suffix + out_path.suffix)
    _save_figure(
        fig,
        target,
        dpi=dpi,
        auto_save=bool(fig_cfg.get('auto_save_timestamped', False)),
        timestamp_dir=str(fig_cfg.get('timestamp_dir', 'timestamped_plots')),
    )
    plt.close(fig)

    pv_fig = create_pv_figure(df, fig_cfg)
    if pv_fig is not None:
        pv_target = out_path.with_name(out_path.stem + suffix + '_pV' + out_path.suffix)
        _save_figure(
            pv_fig,
            pv_target,
            dpi=int((fig_cfg.get('pv_plot', {}) or {}).get('dpi', dpi)),
            auto_save=bool(fig_cfg.get('auto_save_timestamped', False)),
            timestamp_dir=str(fig_cfg.get('timestamp_dir', 'timestamped_plots')),
        )
        plt.close(pv_fig)


def plot_results(
    df,
    out_path: Path,
    dtheta_out_deg: float,
    cycle_deg: float,
    angle_ref_mode: str = 'FIRE_TDC',
    valve_events: dict | None = None,
    overlap: dict | None = None,
    slot_events: dict | None = None,
    timing_validation: dict | None = None,
    closed_cycle_summary: dict | None = None,
    style: dict | None = None,
    crank_angle_offset_deg: float = 0.0,
):
    del dtheta_out_deg, overlap, slot_events  # intentional, kept for API compatibility
    style = _normalize_style(style)
    figures = style.get('figures', []) or []
    if not figures:
        figures = list(DEFAULT_STYLE['figures'])
    for fig_cfg in figures:
        if not isinstance(fig_cfg, dict):
            continue
        _plot_one_layout(
            df=df,
            out_path=out_path,
            fig_cfg=fig_cfg,
            cycle_deg=cycle_deg,
            angle_ref_mode=angle_ref_mode,
            valve_events=valve_events,
            timing_validation=timing_validation,
            closed_cycle_summary=closed_cycle_summary,
            crank_angle_offset_deg=crank_angle_offset_deg,
        )
