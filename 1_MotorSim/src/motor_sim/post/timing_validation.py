from __future__ import annotations

import json
from pathlib import Path

from .phase_logic import reference_points


def _round1_scalar(x):
    if x is None:
        return None
    if isinstance(x, (bool, str)):
        return x
    try:
        return round(float(x), 1)
    except Exception:
        return x


def _round1_obj(obj):
    if isinstance(obj, dict):
        return {k: _round1_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round1_obj(v) for v in obj]
    return _round1_scalar(obj)


def round_timing_validation_obj(obj):
    return _round1_obj(obj)


def _to_mod(value: float | None, cycle_deg: float) -> float | None:
    if value is None:
        return None
    return float(value) % float(cycle_deg)


def _signed_offset(angle_deg: float, ref_deg: float, cycle_deg: float = 720.0) -> float:
    half = float(cycle_deg) / 2.0
    return float(((float(angle_deg) - float(ref_deg) + half) % float(cycle_deg)) - half)


def format_timing_validation_console(summary: dict) -> str:
    s = _round1_obj(summary or {})
    lines = [
        "[TIMING] ------------------------------",
        f"[TIMING] Plausibel : {s.get('timing_plausible')}",
        f"[TIMING] Gründe    : {', '.join(s.get('reasons', [])) if s.get('reasons') else '-'}",
        f"[TIMING] LWOT      : {s.get('LWOT_deg')}",
        f"[TIMING] ZOT       : {s.get('ZOT_deg')}",
        f"[TIMING] IVO       : {s.get('IVO_deg')}",
        f"[TIMING] IVC       : {s.get('IVC_deg')}",
        f"[TIMING] EVO       : {s.get('EVO_deg')}",
        f"[TIMING] EVC       : {s.get('EVC_deg')}",
        f"[TIMING] IVO rel   : {s.get('IVO_rel_gas_exchange_tdc_deg')}",
        f"[TIMING] IVC rel   : {s.get('IVC_rel_intake_bdc_deg')}",
        f"[TIMING] EVO rel   : {s.get('EVO_rel_power_bdc_deg')}",
        f"[TIMING] EVC rel   : {s.get('EVC_rel_gas_exchange_tdc_deg')}",
        f"[TIMING] SOC rel   : {s.get('SOC_rel_ZOT_deg')}",
        f"[TIMING] SOC mod   : {s.get('SOC_mod_cycle_deg')}",
        f"[TIMING] CA50 rel  : {s.get('CA50_rel_ZOT_deg')}",
        f"[TIMING] CA50 mod  : {s.get('CA50_mod_cycle_deg')}",
        f"[TIMING] Intake d  : {s.get('intake_duration_mod_deg')}",
        f"[TIMING] Exhaust d : {s.get('exhaust_duration_mod_deg')}",
        f"[TIMING] Overlap   : {s.get('overlap_simple_deg')}",
        "[TIMING] ------------------------------",
    ]
    return "\n".join(lines)


def validate_4t_timing(
    valve_events: dict,
    cycle_deg: float = 720.0,
    angle_ref_mode: str = 'FIRE_TDC',
    soc_rel_zuend_ot_deg: float | None = None,
    ca50_rel_zuend_ot_deg: float | None = None,
    crank_angle_offset_deg: float = 0.0,
) -> dict:
    refs = reference_points(cycle_deg=cycle_deg, angle_ref_mode=angle_ref_mode, crank_angle_offset_deg=crank_angle_offset_deg)
    out = {
        'cycle_deg': float(cycle_deg),
        'angle_ref_mode': str(angle_ref_mode),
        **refs,
        'LWOT_deg': float(refs['gas_exchange_tdc_deg']),
        'ZOT_deg': float(refs['firing_tdc_deg']),
    }
    for key in ('IVO_deg', 'IVC_deg', 'EVO_deg', 'EVC_deg'):
        val = valve_events.get(key)
        out[key] = _to_mod(val, cycle_deg) if val is not None else None

    ivo = out.get('IVO_deg')
    ivc = out.get('IVC_deg')
    evo = out.get('EVO_deg')
    evc = out.get('EVC_deg')

    if ivo is not None:
        out['IVO_rel_gas_exchange_tdc_deg'] = _signed_offset(ivo, refs['gas_exchange_tdc_deg'], cycle_deg)
    if ivc is not None:
        out['IVC_rel_intake_bdc_deg'] = _signed_offset(ivc, refs['intake_bdc_deg'], cycle_deg)
    if evo is not None:
        out['EVO_rel_power_bdc_deg'] = _signed_offset(evo, refs['power_bdc_deg'], cycle_deg)
    if evc is not None:
        out['EVC_rel_gas_exchange_tdc_deg'] = _signed_offset(evc, refs['gas_exchange_tdc_deg'], cycle_deg)

    zot = float(refs['firing_tdc_deg'])
    if soc_rel_zuend_ot_deg is not None:
        soc_rel = float(soc_rel_zuend_ot_deg)
        out['SOC_rel_ZOT_deg'] = soc_rel
        out['SOC_mod_cycle_deg'] = float((zot + soc_rel) % float(cycle_deg))
    else:
        out['SOC_rel_ZOT_deg'] = None
        out['SOC_mod_cycle_deg'] = None

    if ca50_rel_zuend_ot_deg is not None:
        ca50_rel = float(ca50_rel_zuend_ot_deg)
        out['CA50_rel_ZOT_deg'] = ca50_rel
        out['CA50_mod_cycle_deg'] = float((zot + ca50_rel) % float(cycle_deg))
    else:
        out['CA50_rel_ZOT_deg'] = None
        out['CA50_mod_cycle_deg'] = None

    plausible = True
    reasons: list[str] = []
    if None in (ivo, ivc, evo, evc):
        plausible = False
        reasons.append('missing_events')
    else:
        intake_dur = float((ivc - ivo) % cycle_deg)
        exhaust_dur = float((evc - evo) % cycle_deg)
        overlap = max(0.0, float(evc - ivo)) if ivo <= evc else 0.0
        out['intake_duration_mod_deg'] = intake_dur
        out['exhaust_duration_mod_deg'] = exhaust_dur
        out['overlap_simple_deg'] = overlap
        if intake_dur <= 0.0:
            plausible = False
            reasons.append('intake_duration_nonpositive')
        if exhaust_dur <= 0.0:
            plausible = False
            reasons.append('exhaust_duration_nonpositive')
        if intake_dur > cycle_deg:
            plausible = False
            reasons.append('intake_duration_gt_cycle')
        if exhaust_dur > cycle_deg:
            plausible = False
            reasons.append('exhaust_duration_gt_cycle')

    out['timing_plausible'] = plausible
    out['reasons'] = reasons
    return out


def write_timing_validation(summary: dict, out_path: Path) -> Path:
    path = out_path.with_name(out_path.stem + '_timing_validation.json')
    path.write_text(json.dumps(_round1_obj(summary), indent=2), encoding='utf-8')
    return path
