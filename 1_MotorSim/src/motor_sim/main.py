from __future__ import annotations

import json
import numpy as np
import pandas as pd

from motor_sim.config import load_config
from motor_sim.core.builder import ModelBuilder
from motor_sim.core.integrator import SciPyIntegrator, RK4FixedIntegrator
from motor_sim.post.export_csv import ensure_dir, write_csv
from motor_sim.post.plotting import plot_results
from motor_sim.post.energy_balance import energy_balance_from_dataframe, write_energy_summary
from motor_sim.post.overlap import valve_overlap_segments
from motor_sim.post.phase_logic import ideal_phase_array, reference_points
from motor_sim.post.timing_validation import (
    validate_4t_timing,
    write_timing_validation,
    format_timing_validation_console,
    round_timing_validation_obj,
)
from motor_sim.post.closed_cycle import (
    find_valve_event_series,
    canonical_valve_events,
    build_closed_cycle_reference,
    write_closed_cycle_summary,
)
from motor_sim.post.slot_events import summarize_slot_events
from motor_sim.post.timing_csv import write_timing_csv
from motor_sim.post.steuerdiagramm import plot_steuerdiagramm
from motor_sim.post.cycle_selector import select_last_complete_cycles
from motor_sim.submodels.combustion import combustion_angle_summary
from motor_sim.post.cycle_convergence import (
    compute_cycle_metrics,
    compare_cycle_metrics,
    write_cycle_convergence_summary,
)
from motor_sim.plot_config import resolve_plot_style
from motor_sim.paths import resolve_output_dir
from motor_sim.post.state_decode import internal_energy_from_mass_temp


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def _conv_mark(state: str) -> str:
    if state == "steady":
        return f"{GREEN}+{RESET}"
    if state == "not_steady":
        return f"{RED}-{RESET}"
    return f"{YELLOW}~{RESET}"


def _safe_state_ok(states: dict, name: str):
    state = states.get(name)
    if not isinstance(state, dict):
        return None
    return bool(state.get("ok", False))


def _safe_rel_change_pct(states: dict, name: str):
    state = states.get(name)
    if not isinstance(state, dict):
        return None
    value = state.get("rel_change")
    if value is None:
        return None
    try:
        return 100.0 * float(value)
    except Exception:
        return None


def _state_idx_with_fallback(S, primary_name: str, fallback_name: str):
    """Return (index, chosen_name) preferring `primary_name`, else `fallback_name`."""
    if primary_name in S.idx:
        return S.i(primary_name), primary_name
    if fallback_name in S.idx:
        return S.i(fallback_name), fallback_name
    raise KeyError(f"Neither state '{primary_name}' nor '{fallback_name}' exists in StateIndex")


def _state_value_or_derived_energy(yj, idx_m: int | None, idx_T: int | None, idx_U: int | None, gas_R: float, gas_cp: float):
    if idx_U is not None:
        return float(yj[idx_U])
    if idx_m is not None and idx_T is not None:
        return internal_energy_from_mass_temp(float(yj[idx_m]), float(yj[idx_T]), gas_R, gas_cp)
    return float("nan")


def format_cycle_convergence_compact(
    cycle_index: int,
    checked: bool,
    converged: bool,
    consecutive_ok: int,
    required_consecutive_cycles: int,
    min_cycles_before_check: int,
    state_flags: dict | None = None,
) -> str:
    if not checked:
        return (
            f"[CONV] {_conv_mark('warmup')} "
            f"cycle={int(cycle_index):02d} "
            f"warmup min={int(min_cycles_before_check)}"
        )

    parts = [
        f"[CONV] {_conv_mark('steady' if converged else 'not_steady')}",
        f"cycle={int(cycle_index):02d}",
        f"steady={int(consecutive_ok)}/{int(required_consecutive_cycles)}",
    ]

    state_flags = state_flags or {}
    for key in ("mass", "temp", "imep", "fuel", "q"):
        ok = _safe_state_ok(state_flags, key)
        if ok is None:
            continue
        parts.append(f"{key}={'OK' if ok else 'NO'}")

    imep_rel_pct = _safe_rel_change_pct(state_flags, "imep")
    if imep_rel_pct is not None:
        parts.append(f"imep_d={imep_rel_pct:.2f}%")

    return " ".join(parts)


def _build_cycle_records(t, Y, model, ctx, S, active, idx_m_active, active_energy_idx, active_energy_name, cyl_state_idx):
    records = []
    gas_R = float(ctx.gas.R)
    gas_cp = float(ctx.gas.cp)
    for j, ti in enumerate(t):
        yj = Y[:, j]
        _ = model.rhs(float(ti), yj)

        rec = {
            "t_s": float(ti),
            "theta_deg": ctx.signals.get("theta_deg"),
            "theta_local_deg": ctx.signals.get("theta_local_deg"),
            "p_cyl_pa": ctx.signals.get("p"),
            "p_cyl_mean_pa": ctx.signals.get("p_cyl_mean_pa"),
            "V_m3": ctx.signals.get("V"),
            "V_total_m3": ctx.signals.get("V_total_m3"),
            "x_m": ctx.signals.get("x"),
            "mdot_in_kg_s": ctx.signals.get("mdot_in", 0.0),
            "mdot_out_kg_s": ctx.signals.get("mdot_out", 0.0),
            "A_in_m2": ctx.signals.get("A_in", 0.0),
            "A_ex_m2": ctx.signals.get("A_ex", 0.0),
            "alphaK_in": ctx.signals.get("valves__alphaK_in"),
            "alphaK_ex": ctx.signals.get("valves__alphaK_ex"),
            "alphaV_in": ctx.signals.get("valves__alphaV_in"),
            "alphaV_ex": ctx.signals.get("valves__alphaV_ex"),
            "A_piston_m2": ctx.signals.get("valves__A_piston_m2"),
            "valve_count_in": ctx.signals.get("valves__count_in"),
            "valve_count_ex": ctx.signals.get("valves__count_ex"),
            "A_in_valve_single_m2": ctx.signals.get("valves__A_in_valve_single_m2"),
            "A_ex_valve_single_m2": ctx.signals.get("valves__A_ex_valve_single_m2"),
            "A_in_valve_m2": ctx.signals.get("valves__A_in_valve_m2"),
            "A_ex_valve_m2": ctx.signals.get("valves__A_ex_valve_m2"),
            "qdot_combustion_W": ctx.signals.get("qdot_combustion_W", 0.0),
            "xb_combustion": ctx.signals.get("xb_combustion", 0.0),
            "dq_dtheta_combustion_J_per_deg": ctx.signals.get("dq_dtheta_combustion_J_per_deg", 0.0),
            "active_user_cylinder": active,
            "state_representation": ctx.signals.get("state_representation"),
            "m_int_plenum_kg": ctx.signals.get("m_int_plenum_kg"),
            "T_int_plenum_K": ctx.signals.get("T_int_plenum_K"),
            "U_int_plenum_J": ctx.signals.get("U_int_plenum_J"),
            "p_int_plenum_pa": ctx.signals.get("p_int_plenum_pa"),
            "m_ex_plenum_kg": ctx.signals.get("m_ex_plenum_kg"),
            "T_ex_plenum_K": ctx.signals.get("T_ex_plenum_K"),
            "U_ex_plenum_J": ctx.signals.get("U_ex_plenum_J"),
            "p_ex_plenum_pa": ctx.signals.get("p_ex_plenum_pa"),
            "mdot_feed_int_kg_s": ctx.signals.get("mdot_feed_int_kg_s"),
            "mdot_discharge_ex_kg_s": ctx.signals.get("mdot_discharge_ex_kg_s"),
            "A_throttle_m2": ctx.signals.get("A_throttle_m2"),
            "Cd_throttle": ctx.signals.get("Cd_throttle"),
            "p_upstream_throttle_pa": ctx.signals.get("p_upstream_throttle_pa"),
            "T_upstream_throttle_K": ctx.signals.get("T_upstream_throttle_K"),
        }

        rec["m_cyl_kg"] = float(yj[idx_m_active])
        rec["T_cyl_K"] = float(ctx.signals.get(f"{active}__T_cyl_K", ctx.signals.get("T_cyl_K", np.nan)))
        rec["U_cyl_J_state"] = _state_value_or_derived_energy(
            yj,
            idx_m_active,
            cyl_state_idx[active].get("T_cyl"),
            cyl_state_idx[active].get("U_cyl"),
            gas_R,
            gas_cp,
        )
        rec["lift_in_mm"] = ctx.signals.get(f"{active}__lift_in_mm")
        rec["lift_ex_mm"] = ctx.signals.get(f"{active}__lift_ex_mm")

        for cyl in ctx.cylinders:
            prefix = cyl.name
            idxs = cyl_state_idx[prefix]
            rec[f"{prefix}__m_rin_kg_state"] = float(yj[idxs["m_rin"]])
            rec[f"{prefix}__T_rin_K_state"] = float(ctx.signals.get(f"{prefix}__T_rin_K", np.nan))
            rec[f"{prefix}__U_rin_J_state"] = _state_value_or_derived_energy(yj, idxs["m_rin"], idxs.get("T_rin"), idxs.get("U_rin"), gas_R, gas_cp)
            rec[f"{prefix}__m_rex_kg_state"] = float(yj[idxs["m_rex"]])
            rec[f"{prefix}__T_rex_K_state"] = float(ctx.signals.get(f"{prefix}__T_rex_K", np.nan))
            rec[f"{prefix}__U_rex_J_state"] = _state_value_or_derived_energy(yj, idxs["m_rex"], idxs.get("T_rex"), idxs.get("U_rex"), gas_R, gas_cp)
            rec[f"{prefix}__m_cyl_kg"] = float(yj[idxs["m_cyl"]])
            rec[f"{prefix}__T_cyl_K"] = float(ctx.signals.get(f"{prefix}__T_cyl_K", np.nan))
            rec[f"{prefix}__U_cyl_J_state"] = _state_value_or_derived_energy(yj, idxs["m_cyl"], idxs.get("T_cyl"), idxs.get("U_cyl"), gas_R, gas_cp)

            for k, v in ctx.signals.items():
                if k.startswith(prefix + "__"):
                    rec[k] = v

        records.append(rec)

    return records


def run_case(config_path: str) -> int:
    config_path = str(config_path)
    cfg = load_config(config_path)
    plot_style = resolve_plot_style(config_path, getattr(cfg, "plot_style", {}))
    S, ctx, model, (t0, _t_end_unused), y0 = ModelBuilder(cfg).build()

    active = ctx.cylinder.name
    idx_m_active = S.i(f"m__{active}")
    active_energy_idx, active_energy_name = _state_idx_with_fallback(S, f"T__{active}", f"U__{active}")

    cyl_state_idx = {}
    for cyl in ctx.cylinders:
        prefix = cyl.name
        cyl_state_idx[prefix] = {
            "m_rin": S.i(f"m_rin__{prefix}"),
            "T_rin": S.idx.get(f"T_rin__{prefix}"),
            "U_rin": S.idx.get(f"U_rin__{prefix}"),
            "m_rex": S.i(f"m_rex__{prefix}"),
            "T_rex": S.idx.get(f"T_rex__{prefix}"),
            "U_rex": S.idx.get(f"U_rex__{prefix}"),
            "m_cyl": S.i(f"m__{prefix}"),
            "T_cyl": S.idx.get(f"T__{prefix}"),
            "U_cyl": S.idx.get(f"U__{prefix}"),
        }

    cycle_period_s = float(np.deg2rad(float(ctx.engine.cycle_deg)) / float(ctx.engine.omega_rad_s))
    n_cycles_target = max(
        int(getattr(cfg.simulation, "n_cycles_compute", cfg.simulation.n_cycles_store)),
        int(cfg.simulation.n_cycles_store),
    )

    conv_cfg = getattr(cfg.simulation, "cycle_convergence", None)
    convergence_enabled = bool(getattr(conv_cfg, "enabled", False)) if conv_cfg is not None else False

    all_records = []
    cycle_history = []
    prev_metrics = None
    consecutive_ok = 0
    converged_at_cycle = None

    t_cycle_start = float(t0)
    y_cycle_start = np.array(y0, dtype=float)

    for cycle_idx in range(n_cycles_target):
        t_cycle_end = t_cycle_start + cycle_period_s

        if cfg.simulation.integrator.type == "scipy":
            integ = SciPyIntegrator(
                model=model,
                t0=t_cycle_start,
                t_end=t_cycle_end,
                y0=y_cycle_start,
                cfg=cfg.simulation.integrator,
                dt_out=cfg.simulation.output.dt_out_s,
            )
            t_seg, Y_seg = integ.run()
        elif cfg.simulation.integrator.type == "rk4_fixed":
            integ = RK4FixedIntegrator(
                model=model,
                t0=t_cycle_start,
                t_end=t_cycle_end,
                y0=y_cycle_start,
                dt_internal=cfg.simulation.integrator.dt_internal_s,
                dt_out=cfg.simulation.output.dt_out_s,
            )
            t_seg, Y_seg = integ.run()
        else:
            raise ValueError(f"Unknown integrator.type: {cfg.simulation.integrator.type}")

        records_cycle = _build_cycle_records(
            t_seg, Y_seg, model, ctx, S, active, idx_m_active, active_energy_idx, active_energy_name, cyl_state_idx
        )

        if cycle_idx > 0 and records_cycle:
            records_cycle = records_cycle[1:]

        all_records.extend(records_cycle)

        metrics = {}
        cycle_check = None

        if convergence_enabled and records_cycle:
            df_cycle = pd.DataFrame.from_records(records_cycle)
            metrics = compute_cycle_metrics(df_cycle, Y_seg[:, -1], ctx, S, conv_cfg)

            min_cycles_before_check = int(getattr(conv_cfg, "min_cycles_before_check", 1))
            required_consecutive_cycles = int(getattr(conv_cfg, "required_consecutive_cycles", 1))

            if prev_metrics is not None and (cycle_idx + 1) >= min_cycles_before_check:
                cycle_check = compare_cycle_metrics(prev_metrics, metrics, conv_cfg)
                cycle_converged = bool(cycle_check.get("converged", False))
                consecutive_ok = consecutive_ok + 1 if cycle_converged else 0

                if bool(getattr(conv_cfg, "verbose", True)):
                    print(
                        format_cycle_convergence_compact(
                            cycle_index=cycle_idx + 1,
                            checked=True,
                            converged=cycle_converged,
                            consecutive_ok=consecutive_ok,
                            required_consecutive_cycles=required_consecutive_cycles,
                            min_cycles_before_check=min_cycles_before_check,
                            state_flags=cycle_check.get("states", {}),
                        )
                    )

                if cycle_converged and consecutive_ok >= required_consecutive_cycles:
                    converged_at_cycle = cycle_idx + 1

                    if (
                        bool(getattr(conv_cfg, "stop_when_converged", True))
                        and converged_at_cycle >= int(cfg.simulation.n_cycles_store)
                    ):
                        cycle_history.append(
                            {
                                "cycle_index": cycle_idx + 1,
                                "metrics": metrics,
                                "check": cycle_check,
                                "consecutive_ok": consecutive_ok,
                            }
                        )
                        t_cycle_start = float(t_seg[-1])
                        y_cycle_start = np.array(Y_seg[:, -1], dtype=float)
                        break
            else:
                if bool(getattr(conv_cfg, "verbose", True)):
                    print(
                        format_cycle_convergence_compact(
                            cycle_index=cycle_idx + 1,
                            checked=False,
                            converged=False,
                            consecutive_ok=consecutive_ok,
                            required_consecutive_cycles=required_consecutive_cycles,
                            min_cycles_before_check=min_cycles_before_check,
                            state_flags={},
                        )
                    )

            prev_metrics = metrics

        cycle_history.append(
            {
                "cycle_index": cycle_idx + 1,
                "metrics": metrics,
                "check": cycle_check,
                "consecutive_ok": consecutive_ok,
            }
        )

        t_cycle_start = float(t_seg[-1])
        y_cycle_start = np.array(Y_seg[:, -1], dtype=float)

    df_all = pd.DataFrame.from_records(all_records)

    df, cycle_window = select_last_complete_cycles(
        df_all,
        cycle_deg=ctx.engine.cycle_deg,
        n_cycles_store=cfg.simulation.n_cycles_store,
    )

    active_offset_deg = 0.0
    for uc in cfg.user_cylinders:
        if uc.name == cfg.active_user_cylinder:
            active_offset_deg = float(uc.crank_angle_offset_deg)
            break

    if "theta_deg" in df.columns:
        df["theta_global_deg_mod"] = np.mod(
            df["theta_deg"].to_numpy(dtype=float),
            float(ctx.engine.cycle_deg),
        )
    if "theta_local_deg" in df.columns:
        df["theta_local_deg_mod"] = np.mod(
            df["theta_local_deg"].to_numpy(dtype=float),
            float(ctx.engine.cycle_deg),
        )

    out_dir = ensure_dir(resolve_output_dir(config_path, cfg.output_files.out_dir))
    plot_path = out_dir / cfg.output_files.plot_name

    valve_events = {}
    overlap = {}
    slot_events = {}
    timing_validation = {}
    closed_cycle_summary = {}

    df["ideal_phase"] = ideal_phase_array(
        df["theta_deg"].to_numpy(dtype=float),
        cycle_deg=ctx.engine.cycle_deg,
        angle_ref_mode=cfg.angle_reference.mode,
        crank_angle_offset_deg=active_offset_deg,
    )

    thresholds = getattr(cfg, "thresholds", {}) if hasattr(cfg, "thresholds") else {}
    lift_threshold_mm = float(thresholds.get("lift_threshold_mm", 0.1))
    slot_area_threshold_m2 = float(
        thresholds.get(
            "slot_area_threshold_m2",
            getattr(cfg.postprocess.slot_events, "area_threshold_m2", 1e-7),
        )
    )

    try:
        event_series = find_valve_event_series(df, lift_threshold_mm=lift_threshold_mm)
        valve_events = canonical_valve_events(event_series, cycle_deg=ctx.engine.cycle_deg)

        if valve_events:
            if (
                "IVO_deg" in valve_events
                and "IVC_deg" in valve_events
                and valve_events["IVO_deg"] is not None
                and valve_events["IVC_deg"] is not None
            ):
                valve_events["intake_duration_deg"] = float(
                    (float(valve_events["IVC_deg"]) - float(valve_events["IVO_deg"]))
                    % float(ctx.engine.cycle_deg)
                )

            if (
                "EVO_deg" in valve_events
                and "EVC_deg" in valve_events
                and valve_events["EVO_deg"] is not None
                and valve_events["EVC_deg"] is not None
            ):
                valve_events["exhaust_duration_deg"] = float(
                    (float(valve_events["EVC_deg"]) - float(valve_events["EVO_deg"]))
                    % float(ctx.engine.cycle_deg)
                )

            valve_events["cycle_deg"] = float(ctx.engine.cycle_deg)
            valve_events["event_series"] = event_series

            comb_cfg = getattr(cfg, "energy_models", {}).get("combustion", {}) if hasattr(cfg, "energy_models") else {}
            comb_angles = (
                combustion_angle_summary(
                    comb_cfg,
                    cycle_deg=float(ctx.engine.cycle_deg),
                    zot_deg=float(
                        reference_points(
                            cycle_deg=float(ctx.engine.cycle_deg),
                            angle_ref_mode=cfg.angle_reference.mode,
                            crank_angle_offset_deg=active_offset_deg,
                        )["firing_tdc_deg"]
                    ),
                )
                if bool(comb_cfg.get("enabled", False))
                else {}
            )

            timing_validation = validate_4t_timing(
                valve_events,
                cycle_deg=ctx.engine.cycle_deg,
                angle_ref_mode=cfg.angle_reference.mode,
                soc_rel_zuend_ot_deg=comb_angles.get("soc_rel_zuend_ot_deg") if comb_angles else None,
                ca50_rel_zuend_ot_deg=comb_angles.get("ca50_rel_zuend_ot_deg") if comb_angles else None,
                crank_angle_offset_deg=active_offset_deg,
            )

            write_timing_validation(timing_validation, plot_path)
            print(format_timing_validation_console(timing_validation))

            ref_cols, closed_cycle_summary = build_closed_cycle_reference(
                df,
                event_series,
                cycle_deg=ctx.engine.cycle_deg,
                angle_ref_mode=cfg.angle_reference.mode,
                crank_angle_offset_deg=active_offset_deg,
            )

            if ref_cols:
                for col, vals in ref_cols.items():
                    df[col] = vals
                write_closed_cycle_summary(closed_cycle_summary, plot_path)

    except Exception as exc:
        print(f"[WARN] Valve/timing processing failed: {exc}")

    try:
        overlap = valve_overlap_segments(df, lift_threshold_mm=lift_threshold_mm)
    except Exception as exc:
        print(f"[WARN] Valve overlap detection failed: {exc}")

    try:
        slot_events = summarize_slot_events(
            df,
            area_threshold_m2=slot_area_threshold_m2,
            per_group=cfg.postprocess.slot_events.per_group,
        )
    except Exception as exc:
        print(f"[WARN] Slot event detection failed: {exc}")

    csv_path = write_csv(df, out_dir, cfg.output_files.csv_name)

    try:
        if valve_events:
            write_timing_csv(valve_events, plot_path)
            plot_steuerdiagramm(
                df,
                valve_events,
                plot_path,
                cycle_deg=ctx.engine.cycle_deg,
                angle_ref_mode=cfg.angle_reference.mode,
                overlap=overlap,
                slot_events=slot_events,
                plot_theta_min_deg=cfg.angle_reference.plot_theta_min_deg,
                plot_theta_max_deg=cfg.angle_reference.plot_theta_max_deg,
                style=plot_style,
                crank_angle_offset_deg=active_offset_deg,
            )
    except Exception as exc:
        print(f"[WARN] Timing export failed: {exc}")

    try:
        plot_results(
            df,
            plot_path,
            cfg.simulation.output.dtheta_out_deg,
            cycle_deg=ctx.engine.cycle_deg,
            angle_ref_mode=cfg.angle_reference.mode,
            valve_events=valve_events,
            overlap=overlap,
            slot_events=slot_events,
            timing_validation=timing_validation,
            closed_cycle_summary=closed_cycle_summary,
            style=plot_style,
            crank_angle_offset_deg=active_offset_deg,
        )
    except Exception as exc:
        print(f"[WARN] Plot generation failed: {exc}")

    energy_summary = energy_balance_from_dataframe(
        df,
        gas_R=cfg.gas.R_J_per_kgK,
        gas_cp=cfg.gas.cp_J_per_kgK,
        cfg_energy=getattr(cfg, "energy_models", {}),
        angle_ref_mode=cfg.angle_reference.mode,
        crank_angle_offset_deg=active_offset_deg,
    )
    energy_summary_path = write_energy_summary(energy_summary, out_dir)

    cycle_convergence_summary = {
        "enabled": convergence_enabled,
        "computed_cycles_target": n_cycles_target,
        "computed_cycles_actual": len(cycle_history),
        "converged": converged_at_cycle is not None,
        "converged_at_cycle": converged_at_cycle,
        "required_consecutive_cycles": int(getattr(conv_cfg, "required_consecutive_cycles", 0)) if conv_cfg is not None else 0,
        "min_cycles_before_check": int(getattr(conv_cfg, "min_cycles_before_check", 0)) if conv_cfg is not None else 0,
        "stop_when_converged": bool(getattr(conv_cfg, "stop_when_converged", False)) if conv_cfg is not None else False,
        "monitored_states": list(getattr(conv_cfg, "monitored_states", [])) if conv_cfg is not None else [],
        "history": cycle_history,
    }
    cycle_convergence_path = write_cycle_convergence_summary(cycle_convergence_summary, out_dir)

    summary = {
        "cylinder": {
            "all_user_cylinders": [uc.name for uc in cfg.user_cylinders],
            "enabled_user_cylinders": [uc.name for uc in cfg.user_cylinders if uc.enabled],
            "active_user_cylinder": cfg.active_user_cylinder,
            "crank_angle_offsets_deg": {uc.name: uc.crank_angle_offset_deg for uc in cfg.user_cylinders},
            "n_enabled_cylinders": len(ctx.cylinders),
        },
        "plena": {
            "enabled": cfg.plena.enabled,
            "intake_volume_m3": cfg.plena.intake.volume_m3,
            "exhaust_volume_m3": cfg.plena.exhaust.volume_m3,
        },
        "throttle": {
            "enabled": cfg.throttle.enabled,
            "diameter_m": cfg.throttle.diameter_m,
            "cd": cfg.throttle.cd,
            "position": cfg.throttle.position,
            "position_mode": cfg.throttle.position_mode,
            "A_max_m2": cfg.throttle.A_max_m2,
            "T_upstream_K": cfg.throttle.T_upstream_K,
            "p_upstream_pa": cfg.throttle.p_upstream_pa,
        },
        "runners": {
            uc.name: {
                "intake": {
                    "length_m": uc.runners.intake.length_m,
                    "diameter_m": uc.runners.intake.diameter_m,
                    "volume_m3": uc.runners.intake.volume_m3,
                    "zeta_local": uc.runners.intake.zeta_local,
                    "friction_factor": uc.runners.intake.friction_factor,
                },
                "exhaust": {
                    "length_m": uc.runners.exhaust.length_m,
                    "diameter_m": uc.runners.exhaust.diameter_m,
                    "volume_m3": uc.runners.exhaust.volume_m3,
                    "zeta_local": uc.runners.exhaust.zeta_local,
                    "friction_factor": uc.runners.exhaust.friction_factor,
                },
            }
            for uc in cfg.user_cylinders
        },
        "energy_balance": energy_summary.to_dict(),
        "timing_validation": round_timing_validation_obj(timing_validation),
        "closed_cycle_summary": closed_cycle_summary,
        "cycle_window": cycle_window,
        "simulation_cycles_compute": n_cycles_target,
        "simulation_cycles_store": int(cfg.simulation.n_cycles_store),
        "cycle_convergence": cycle_convergence_summary,
    }

    (out_dir / "group_contributions_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] CSV:  {csv_path}")
    print(f"[OK] Plot: {plot_path}")
    if valve_events:
        print(f"[OK] Valve events: {plot_path.with_name(plot_path.stem + '_steuerzeiten.csv')}")
        print(f"[OK] Steuerzeiten-Diagramm: {plot_path.with_name(plot_path.stem + '_steuerzeiten.png')}")
        print(f"[OK] Steuerkreisdiagramm: {plot_path.with_name(plot_path.stem + '_steuerkreis.png')}")
        print(f"[OK] Timing validation: {plot_path.with_name(plot_path.stem + '_timing_validation.json')}")
        if closed_cycle_summary:
            print(f"[OK] Closed-cycle summary: {plot_path.with_name(plot_path.stem + '_closed_cycle_summary.json')}")

    print(f"[INFO] Enabled cylinders: {', '.join([c.name for c in ctx.cylinders])}")
    print(f"[INFO] Dynamic plena enabled: {cfg.plena.enabled}")
    print(
        f"[INFO] Computed cycles target: {n_cycles_target}, "
        f"actual: {len(cycle_history)}, "
        f"stored/plotted cycles: {int(cfg.simulation.n_cycles_store)}"
    )
    print(
        f"[INFO] Cycle convergence: enabled={convergence_enabled}, "
        f"converged={converged_at_cycle is not None}, "
        f"at_cycle={converged_at_cycle}"
    )
    print(f"[OK] Energy summary: {energy_summary_path}")
    print(f"[OK] Cycle convergence summary: {cycle_convergence_path}")
    print(
        f"[INFO] Energy closure residual: "
        f"{energy_summary.closure_residual_J:.3f} J "
        f"({energy_summary.closure_relative_pct:.3f} %)"
    )

    return 0