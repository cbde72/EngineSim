import math


import json
from pathlib import Path
import numpy as np


def _safe_rel_delta(curr: float, prev: float) -> float:
    denom = max(abs(float(prev)), 1e-30)
    return abs(float(curr) - float(prev)) / denom


def _classify_metric(name: str) -> str:
    lname = str(name).lower()
    if 'temp' in lname or lname.endswith('_k'):
        return 'temp'
    if 'mass' in lname or lname.endswith('_kg') or 'fuel' in lname:
        return 'mass'
    return 'other'


def _tolerances(metric_name: str, cfg) -> tuple[float, float, str]:
    kind = _classify_metric(metric_name)
    if kind == 'temp':
        return float(cfg.rel_tol_temp), float(cfg.abs_tol_temp_K), kind
    if kind == 'mass':
        return float(cfg.rel_tol_mass), float(cfg.abs_tol_mass_kg), kind
    return float(getattr(cfg, 'rel_tol_other', 5e-4)), float(getattr(cfg, 'abs_tol_other', 1e-3)), kind




def _temperature_from_state(S, y, gas, mass_name: str, temp_name: str, energy_name: str, default: float = 0.0) -> float:
    if temp_name in S.idx:
        return float(y[S.i(temp_name)])
    if energy_name in S.idx and mass_name in S.idx:
        m = float(y[S.i(mass_name)])
        U = float(y[S.i(energy_name)])
        return float(U / max(m, 1e-12) / gas.cv)
    return float(default)

def compute_cycle_metrics(df_cycle, y_end, ctx, S, cfg) -> dict:
    metrics = {}
    monitored = set(getattr(cfg, 'monitored_states', []) or [])

    if 'cylinder_masses' in monitored:
        for cyl in ctx.cylinders:
            metrics[f'cylinder_mass__{cyl.name}_kg'] = float(y_end[S.i(f'm__{cyl.name}')])
            metrics[f'intake_runner_mass__{cyl.name}_kg'] = float(y_end[S.i(f'm_rin__{cyl.name}')])
            metrics[f'exhaust_runner_mass__{cyl.name}_kg'] = float(y_end[S.i(f'm_rex__{cyl.name}')])
    if 'cylinder_temperatures' in monitored:
        for cyl in ctx.cylinders:
            metrics[f'cylinder_temp__{cyl.name}_K'] = _temperature_from_state(S, y_end, ctx.gas, f'm__{cyl.name}', f'T__{cyl.name}', f'U__{cyl.name}')
            metrics[f'intake_runner_temp__{cyl.name}_K'] = _temperature_from_state(S, y_end, ctx.gas, f'm_rin__{cyl.name}', f'T_rin__{cyl.name}', f'U_rin__{cyl.name}')
            metrics[f'exhaust_runner_temp__{cyl.name}_K'] = _temperature_from_state(S, y_end, ctx.gas, f'm_rex__{cyl.name}', f'T_rex__{cyl.name}', f'U_rex__{cyl.name}')

    if 'intake_plenum_mass' in monitored:
        metrics['intake_plenum_mass_kg'] = float(y_end[S.i('m_int_plenum')])
    if 'exhaust_plenum_mass' in monitored:
        metrics['exhaust_plenum_mass_kg'] = float(y_end[S.i('m_ex_plenum')])
    if 'intake_plenum_temperature' in monitored:
        metrics['intake_plenum_temp_K'] = _temperature_from_state(S, y_end, ctx.gas, 'm_int_plenum', 'T_int_plenum', 'U_int_plenum')
    if 'exhaust_plenum_temperature' in monitored:
        metrics['exhaust_plenum_temp_K'] = _temperature_from_state(S, y_end, ctx.gas, 'm_ex_plenum', 'T_ex_plenum', 'U_ex_plenum')

    if 'imep' in monitored and {'p_cyl_pa', 'V_m3'} <= set(df_cycle.columns):
        p = df_cycle['p_cyl_pa'].to_numpy(dtype=float)
        V = df_cycle['V_m3'].to_numpy(dtype=float)
        if len(p) >= 2 and len(V) >= 2:
            work_J = float(np.trapezoid(p, V))
            Vd = float(ctx.engine.displacement_m3)
            if abs(Vd) > 0.0:
                metrics['imep_pa'] = work_J / Vd
    if 'fuel_mass_per_cycle' in monitored and 'qdot_combustion_W' in df_cycle.columns and 't_s' in df_cycle.columns:
        qdot = df_cycle['qdot_combustion_W'].to_numpy(dtype=float)
        tt = df_cycle['t_s'].to_numpy(dtype=float)
        if len(qdot) >= 2 and len(tt) >= 2:
            q_cycle_J = float(np.trapezoid(qdot, tt))
            comb_cfg = getattr(ctx.cfg, 'energy_models', {}).get('combustion', {}) if hasattr(ctx.cfg, 'energy_models') else {}
            eta = max(float(comb_cfg.get('combustion_efficiency', 1.0)), 1e-30)
            lhv = max(float(comb_cfg.get('fuel_lhv_J_per_kg', 42.5e6)), 1e-30)
            metrics['fuel_mass_per_cycle_kg'] = q_cycle_J / (lhv * eta)
            metrics['released_heat_per_cycle_J'] = q_cycle_J
    return metrics


def compare_cycle_metrics(prev_metrics: dict, curr_metrics: dict, cfg) -> dict:
    compared = []
    all_ok = True
    max_rel = 0.0
    max_abs = 0.0
    for name in sorted(set(prev_metrics.keys()) & set(curr_metrics.keys())):
        prev = float(prev_metrics[name])
        curr = float(curr_metrics[name])
        abs_delta = abs(curr - prev)
        rel_delta = _safe_rel_delta(curr, prev)
        rel_tol, abs_tol, kind = _tolerances(name, cfg)
        ok = (abs_delta <= abs_tol) or (rel_delta <= rel_tol)
        all_ok = all_ok and ok
        max_rel = max(max_rel, rel_delta)
        max_abs = max(max_abs, abs_delta)
        compared.append({
            'name': name,
            'kind': kind,
            'prev': prev,
            'curr': curr,
            'abs_delta': abs_delta,
            'rel_delta': rel_delta,
            'abs_tol': abs_tol,
            'rel_tol': rel_tol,
            'ok': ok,
        })
    failing = [c for c in compared if not c['ok']]
    return {
        'converged': bool(compared) and all_ok,
        'n_metrics': len(compared),
        'max_rel_delta': max_rel,
        'max_abs_delta': max_abs,
        'failing_metrics': failing,
        'metrics': compared,
    }


def summarize_cycle_check(cycle_index: int, result: dict, consecutive_ok: int) -> str:
    lines = [
        f"[STEADY] cycle={cycle_index} converged={result.get('converged')} consecutive_ok={consecutive_ok} checked={result.get('n_metrics', 0)}",
        f"[STEADY] max_abs_delta={result.get('max_abs_delta', 0.0):.6e} max_rel_delta={result.get('max_rel_delta', 0.0):.6e}",
    ]
    failing = result.get('failing_metrics', [])[:8]
    if failing:
        lines.append('[STEADY] failing metrics:')
        for item in failing:
            lines.append(
                f"[STEADY]   {item['name']}: prev={item['prev']:.6e} curr={item['curr']:.6e} "
                f"abs={item['abs_delta']:.6e}/{item['abs_tol']:.6e} rel={item['rel_delta']:.6e}/{item['rel_tol']:.6e}"
            )
    return "\n".join(lines)


def write_cycle_convergence_summary(summary: dict, out_dir: Path) -> Path:
    path = Path(out_dir) / 'cycle_convergence_summary.json'
    path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return path
