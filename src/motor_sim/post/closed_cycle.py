from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .phase_logic import reference_points


def _find_crossings(theta: np.ndarray, signal: np.ndarray, threshold: float):
    th = np.asarray(theta, dtype=float)
    y = np.asarray(signal, dtype=float)
    above = y > float(threshold)
    rising = []
    falling = []
    for i in range(len(th) - 1):
        y0 = y[i] - threshold
        y1 = y[i + 1] - threshold
        if y0 <= 0.0 and y1 > 0.0:
            frac = 0.0 if y1 == y0 else (-y0) / (y1 - y0)
            rising.append(float(th[i] + frac * (th[i + 1] - th[i])))
        elif y0 > 0.0 and y1 <= 0.0:
            frac = 0.0 if y1 == y0 else y0 / (y0 - y1)
            falling.append(float(th[i] + frac * (th[i + 1] - th[i])))
    return rising, falling


def find_valve_event_series(df, lift_threshold_mm: float = 0.1) -> dict:
    theta = df['theta_deg'].to_numpy(dtype=float)
    lift_in = df['lift_in_mm'].to_numpy(dtype=float)
    lift_ex = df['lift_ex_mm'].to_numpy(dtype=float)
    in_open, in_close = _find_crossings(theta, lift_in, lift_threshold_mm)
    ex_open, ex_close = _find_crossings(theta, lift_ex, lift_threshold_mm)
    return {
        'intake_open_abs_deg': in_open,
        'intake_close_abs_deg': in_close,
        'exhaust_open_abs_deg': ex_open,
        'exhaust_close_abs_deg': ex_close,
    }


def canonical_valve_events(event_series: dict, cycle_deg: float = 720.0) -> dict:
    def first_mod(vals):
        if not vals:
            return None
        mods = sorted(float(np.mod(v, cycle_deg)) for v in vals)
        return float(mods[0])
    return {
        'IVO_deg': first_mod(event_series.get('intake_open_abs_deg', [])),
        'IVC_deg': first_mod(event_series.get('intake_close_abs_deg', [])),
        'EVO_deg': first_mod(event_series.get('exhaust_open_abs_deg', [])),
        'EVC_deg': first_mod(event_series.get('exhaust_close_abs_deg', [])),
    }


def _polytropic_n(p1, v1, p2, v2):
    p1 = float(p1); p2 = float(p2); v1 = float(v1); v2 = float(v2)
    if min(p1, p2, v1, v2) <= 0.0 or abs(np.log(v1 / v2)) < 1e-14:
        return None
    return float(np.log(p2 / p1) / np.log(v1 / v2))


def build_closed_cycle_reference(df, event_series: dict, cycle_deg: float = 720.0, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0):
    theta = df['theta_deg'].to_numpy(dtype=float)
    p = df['p_cyl_pa'].to_numpy(dtype=float)
    V = df['V_m3'].to_numpy(dtype=float)
    refs = reference_points(cycle_deg=cycle_deg, angle_ref_mode=angle_ref_mode, crank_angle_offset_deg=crank_angle_offset_deg)
    firing_mod = refs['firing_tdc_deg']
    theta_min = float(theta.min())
    theta_max = float(theta.max())

    firing_candidates = []
    k0 = int(np.floor((theta_min - firing_mod) / cycle_deg)) - 1
    for k in range(k0, k0 + 10):
        ft = firing_mod + k * cycle_deg
        if theta_min <= ft <= theta_max:
            firing_candidates.append(ft)

    IVCs = sorted(float(v) for v in event_series.get('intake_close_abs_deg', []))
    EVOs = sorted(float(v) for v in event_series.get('exhaust_open_abs_deg', []))
    selected = None
    for ft in firing_candidates:
        ivc_before = [v for v in IVCs if v < ft]
        evo_after = [v for v in EVOs if v > ft]
        if ivc_before and evo_after:
            selected = (ivc_before[-1], ft, evo_after[0])
            break
    if selected is None:
        return None, None

    ivc_abs, ft_abs, evo_abs = selected
    p_ref_comp = np.full_like(p, np.nan, dtype=float)
    p_ref_exp = np.full_like(p, np.nan, dtype=float)
    p_ref_cc = np.full_like(p, np.nan, dtype=float)

    mask_comp = (theta >= ivc_abs) & (theta <= ft_abs)
    mask_exp = (theta >= ft_abs) & (theta <= evo_abs)
    if mask_comp.sum() < 2 or mask_exp.sum() < 2:
        return None, None

    i1 = int(np.where(mask_comp)[0][0]); i2 = int(np.where(mask_comp)[0][-1])
    j1 = int(np.where(mask_exp)[0][0]); j2 = int(np.where(mask_exp)[0][-1])

    n_comp = _polytropic_n(p[i1], V[i1], p[i2], V[i2])
    n_exp = _polytropic_n(p[j1], V[j1], p[j2], V[j2])
    if n_comp is not None:
        p_ref_comp[mask_comp] = p[i1] * (V[i1] / V[mask_comp]) ** n_comp
    if n_exp is not None:
        p_ref_exp[mask_exp] = p[j1] * (V[j1] / V[mask_exp]) ** n_exp
    p_ref_cc[:] = np.where(np.isfinite(p_ref_comp), p_ref_comp, p_ref_exp)

    summary = {
        'angle_ref_mode': str(angle_ref_mode),
        'cycle_deg': float(cycle_deg),
        'compression_start_deg': float(ivc_abs),
        'firing_tdc_deg': float(ft_abs),
        'expansion_end_deg': float(evo_abs),
        'compression': {
            'start_deg': float(ivc_abs),
            'end_deg': float(ft_abs),
            'n_polytropic': None if n_comp is None else float(n_comp),
            'pressure_ratio': float(p[i2] / p[i1]),
        },
        'expansion': {
            'start_deg': float(ft_abs),
            'end_deg': float(evo_abs),
            'n_polytropic': None if n_exp is None else float(n_exp),
            'pressure_ratio': float(p[j2] / p[j1]),
        },
    }
    return {
        'p_ref_compression_pa': p_ref_comp,
        'p_ref_expansion_pa': p_ref_exp,
        'p_ref_closed_cycle_pa': p_ref_cc,
    }, summary


def write_closed_cycle_summary(summary: dict, out_path: Path) -> Path:
    path = out_path.with_name(out_path.stem + '_closed_cycle_summary.json')
    path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return path
