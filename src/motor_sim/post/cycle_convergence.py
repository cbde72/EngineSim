from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _safe_rel_change(curr: float, prev: float, floor: float = 1e-12) -> float:
    denom = max(abs(float(prev)), float(floor))
    return abs(float(curr) - float(prev)) / denom


def _integrate_trapz(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or y.size < 2:
        return 0.0
    return float(np.trapezoid(y, x))


def _round_obj(obj: Any, ndigits: int = 6) -> Any:
    if isinstance(obj, dict):
        return {k: _round_obj(v, ndigits=ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_obj(v, ndigits=ndigits) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return round(float(obj), ndigits)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    return obj


def _get_monitored_states(conv_cfg: Any) -> list[str]:
    states = getattr(conv_cfg, "monitored_states", None)
    if states:
        return [str(s) for s in states]

    return [
        "mass",
        "temp",
        "imep",
        "fuel",
        "q",
        "plenum_mass",
        "plenum_temp",
        "runner_mass",
        "runner_temp",
    ]


def _sum_columns(df: pd.DataFrame, suffixes: tuple[str, ...]) -> float:
    cols = [c for c in df.columns if any(c.endswith(s) for s in suffixes)]
    if not cols:
        return 0.0
    return float(df.iloc[-1][cols].astype(float).sum())


def _mean_columns(df: pd.DataFrame, suffixes: tuple[str, ...]) -> float:
    cols = [c for c in df.columns if any(c.endswith(s) for s in suffixes)]
    if not cols:
        return 0.0
    return float(df.iloc[-1][cols].astype(float).mean())


def _compute_imep_pa(df_cycle: pd.DataFrame, ctx: Any) -> float:
    if "p_cyl_pa" not in df_cycle.columns or "V_m3" not in df_cycle.columns:
        return 0.0

    p = df_cycle["p_cyl_pa"].to_numpy(dtype=float)
    v = df_cycle["V_m3"].to_numpy(dtype=float)

    if p.size < 2 or v.size < 2:
        return 0.0

    work_cycle_J = float(np.trapezoid(p, v))

    vd = _to_float(getattr(ctx.engine, "displacement_m3", 0.0), 0.0)
    if vd <= 0.0:
        return 0.0

    return work_cycle_J / vd


def _compute_fuel_mass_kg(df_cycle: pd.DataFrame) -> float:
    if "m_fuel_cycle_kg" in df_cycle.columns:
        return _to_float(df_cycle["m_fuel_cycle_kg"].iloc[-1], 0.0)

    if "mdot_fuel_kg_s" in df_cycle.columns and "t_s" in df_cycle.columns:
        t = df_cycle["t_s"].to_numpy(dtype=float)
        mdot = df_cycle["mdot_fuel_kg_s"].to_numpy(dtype=float)
        return _integrate_trapz(t, mdot)

    if "fuel_mass_kg" in df_cycle.columns:
        vals = df_cycle["fuel_mass_kg"].to_numpy(dtype=float)
        if vals.size:
            return float(vals[-1] - vals[0])

    return 0.0


def _compute_combustion_energy_J(df_cycle: pd.DataFrame) -> float:
    if "q_combustion_cycle_J" in df_cycle.columns:
        return _to_float(df_cycle["q_combustion_cycle_J"].iloc[-1], 0.0)

    if "qdot_combustion_W" in df_cycle.columns and "t_s" in df_cycle.columns:
        t = df_cycle["t_s"].to_numpy(dtype=float)
        qdot = df_cycle["qdot_combustion_W"].to_numpy(dtype=float)
        return _integrate_trapz(t, qdot)

    if "dq_dtheta_combustion_J_per_deg" in df_cycle.columns:
        if "theta_local_deg" in df_cycle.columns:
            th = df_cycle["theta_local_deg"].to_numpy(dtype=float)
        elif "theta_deg" in df_cycle.columns:
            th = df_cycle["theta_deg"].to_numpy(dtype=float)
        else:
            return 0.0
        dq = df_cycle["dq_dtheta_combustion_J_per_deg"].to_numpy(dtype=float)
        return _integrate_trapz(th, dq)

    return 0.0


def compute_cycle_metrics(
    df_cycle: pd.DataFrame,
    y_end: np.ndarray | None,
    ctx: Any,
    S: Any,
    conv_cfg: Any,
) -> dict:
    """
    Build scalar metrics for one complete cycle.

    Expected by main.py:
    - returns a dict with scalar values
    - compare_cycle_metrics(prev, curr, conv_cfg) compares two such dicts
    """
    monitored_states = _get_monitored_states(conv_cfg)

    metrics: dict[str, Any] = {
        "monitored_states": monitored_states,
        "n_samples": int(len(df_cycle)),
    }

    if len(df_cycle) == 0:
        metrics["mass"] = 0.0
        metrics["temp"] = 0.0
        metrics["imep"] = 0.0
        metrics["fuel"] = 0.0
        metrics["q"] = 0.0
        metrics["plenum_mass"] = 0.0
        metrics["plenum_temp"] = 0.0
        metrics["runner_mass"] = 0.0
        metrics["runner_temp"] = 0.0
        return metrics

    # Core cylinder metrics
    metrics["mass"] = _to_float(df_cycle["m_cyl_kg"].iloc[-1], 0.0) if "m_cyl_kg" in df_cycle.columns else 0.0
    metrics["temp"] = _to_float(df_cycle["T_cyl_K"].iloc[-1], 0.0) if "T_cyl_K" in df_cycle.columns else 0.0
    metrics["imep"] = _compute_imep_pa(df_cycle, ctx)
    metrics["fuel"] = _compute_fuel_mass_kg(df_cycle)
    metrics["q"] = _compute_combustion_energy_J(df_cycle)

    # Plena
    plenum_mass = 0.0
    if "m_int_plenum_kg" in df_cycle.columns:
        plenum_mass += _to_float(df_cycle["m_int_plenum_kg"].iloc[-1], 0.0)
    if "m_ex_plenum_kg" in df_cycle.columns:
        plenum_mass += _to_float(df_cycle["m_ex_plenum_kg"].iloc[-1], 0.0)
    metrics["plenum_mass"] = plenum_mass

    plenum_temps = []
    if "T_int_plenum_K" in df_cycle.columns:
        plenum_temps.append(_to_float(df_cycle["T_int_plenum_K"].iloc[-1], 0.0))
    if "T_ex_plenum_K" in df_cycle.columns:
        plenum_temps.append(_to_float(df_cycle["T_ex_plenum_K"].iloc[-1], 0.0))
    metrics["plenum_temp"] = float(np.mean(plenum_temps)) if plenum_temps else 0.0

    # Runner sums across all cylinders
    metrics["runner_mass"] = _sum_columns(
        df_cycle,
        ("__m_rin_kg_state", "__m_rex_kg_state"),
    )
    metrics["runner_temp"] = _mean_columns(
        df_cycle,
        ("__T_rin_K_state", "__T_rex_K_state"),
    )

    # Optional end-state diagnostics
    if y_end is not None:
        try:
            arr = np.asarray(y_end, dtype=float)
            metrics["state_norm_l2"] = float(np.linalg.norm(arr))
            metrics["state_norm_inf"] = float(np.max(np.abs(arr))) if arr.size else 0.0
        except Exception:
            metrics["state_norm_l2"] = 0.0
            metrics["state_norm_inf"] = 0.0

    # Helpful extras for debugging/JSON
    if "t_s" in df_cycle.columns and len(df_cycle) >= 2:
        metrics["cycle_duration_s"] = _to_float(df_cycle["t_s"].iloc[-1] - df_cycle["t_s"].iloc[0], 0.0)
    else:
        metrics["cycle_duration_s"] = 0.0

    if "theta_deg" in df_cycle.columns and len(df_cycle) >= 2:
        metrics["theta_span_deg"] = _to_float(df_cycle["theta_deg"].iloc[-1] - df_cycle["theta_deg"].iloc[0], 0.0)
    else:
        metrics["theta_span_deg"] = 0.0

    return metrics


def compare_cycle_metrics(prev_metrics: dict, curr_metrics: dict, conv_cfg: Any) -> dict:
    """
    Compare two consecutive cycle metric dicts.

    Uses config parameters:
    - rel_tol_mass
    - rel_tol_temp
    - abs_tol_mass_kg
    - abs_tol_temp_K
    - rel_tol_other
    - abs_tol_other
    - monitored_states
    """
    monitored_states = _get_monitored_states(conv_cfg)

    rel_tol_mass = _to_float(getattr(conv_cfg, "rel_tol_mass", 1e-4), 1e-4)
    rel_tol_temp = _to_float(getattr(conv_cfg, "rel_tol_temp", 5e-4), 5e-4)
    abs_tol_mass_kg = _to_float(getattr(conv_cfg, "abs_tol_mass_kg", 1e-8), 1e-8)
    abs_tol_temp_K = _to_float(getattr(conv_cfg, "abs_tol_temp_K", 1e-3), 1e-3)
    rel_tol_other = _to_float(getattr(conv_cfg, "rel_tol_other", rel_tol_mass), rel_tol_mass)
    abs_tol_other = _to_float(getattr(conv_cfg, "abs_tol_other", abs_tol_mass_kg), abs_tol_mass_kg)

    states: dict[str, dict[str, Any]] = {}

    def add_state(name: str, abs_tol: float, rel_tol: float) -> None:
        prev_val = _to_float(prev_metrics.get(name, 0.0), 0.0)
        curr_val = _to_float(curr_metrics.get(name, 0.0), 0.0)
        abs_change = abs(curr_val - prev_val)
        rel_change = _safe_rel_change(curr_val, prev_val)
        ok = (abs_change <= abs_tol) or (rel_change <= rel_tol)

        states[name] = {
            "prev": prev_val,
            "curr": curr_val,
            "abs_change": abs_change,
            "rel_change": rel_change,
            "abs_tol": float(abs_tol),
            "rel_tol": float(rel_tol),
            "ok": bool(ok),
        }

    for name in monitored_states:
        if name == "mass":
            add_state("mass", abs_tol_mass_kg, rel_tol_mass)
        elif name == "temp":
            add_state("temp", abs_tol_temp_K, rel_tol_temp)
        else:
            add_state(name, abs_tol_other, rel_tol_other)

    all_ok = all(bool(v.get("ok", False)) for v in states.values()) if states else False

    return {
        "converged": bool(all_ok),
        "states": states,
        "monitored_states": monitored_states,
    }


def write_cycle_convergence_summary(summary: dict, out_dir: Path | str) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cycle_convergence_summary.json"
    path.write_text(
        json.dumps(_round_obj(summary, ndigits=6), indent=2),
        encoding="utf-8",
    )
    return path