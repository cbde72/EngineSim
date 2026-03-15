from __future__ import annotations

import math
from dataclasses import replace

from motor_sim.core.builder import ModelBuilder



def test_initial_state_matches_configured_plenum_conditions(built_model):
    S = built_model["S"]
    cfg = built_model["cfg"]
    ctx = built_model["ctx"]
    y0 = built_model["y0"]
    gas = ctx.gas

    m_int = y0[S.i("m_int_plenum")]
    T_int = y0[S.i("T_int_plenum")]
    p_int = m_int * gas.R * T_int / cfg.plena.intake.volume_m3
    assert math.isclose(T_int, cfg.plena.intake.T0_K, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(p_int, cfg.plena.intake.p0_pa, rel_tol=1e-12)

    m_ex = y0[S.i("m_ex_plenum")]
    T_ex = y0[S.i("T_ex_plenum")]
    p_ex = m_ex * gas.R * T_ex / cfg.plena.exhaust.volume_m3
    assert math.isclose(T_ex, cfg.plena.exhaust.T0_K, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(p_ex, cfg.plena.exhaust.p0_pa, rel_tol=1e-12)



def test_initial_state_matches_configured_cylinder_and_runner_pressures(built_model):
    S = built_model["S"]
    cfg = built_model["cfg"]
    ctx = built_model["ctx"]
    y0 = built_model["y0"]
    gas = ctx.gas

    runner_defaults = getattr(cfg, "numerics", {}).get("runner_defaults", {})
    min_runner_volume_m3 = float(getattr(cfg, "numerics", {}).get("min_runner_volume_m3", 1e-9))

    for cyl in ctx.cylinders:
        prefix = cyl.name
        rcfg = cyl.runner_cfg or {}
        rin = rcfg.get("intake", {})
        rex = rcfg.get("exhaust", {})

        V_rin = max(float(rin.get("volume_m3", runner_defaults.get("intake_volume_m3", 0.00024))), min_runner_volume_m3)
        T_rin = y0[S.i(f"T_rin__{prefix}")]
        m_rin = y0[S.i(f"m_rin__{prefix}")]
        p_rin = m_rin * gas.R * T_rin / V_rin
        assert math.isclose(p_rin, cfg.plena.intake.p0_pa, rel_tol=1e-12)

        V_rex = max(float(rex.get("volume_m3", runner_defaults.get("exhaust_volume_m3", 0.00024))), min_runner_volume_m3)
        T_rex = y0[S.i(f"T_rex__{prefix}")]
        m_rex = y0[S.i(f"m_rex__{prefix}")]
        p_rex = m_rex * gas.R * T_rex / V_rex
        assert math.isclose(p_rex, cfg.plena.exhaust.p0_pa, rel_tol=1e-12)

        m_cyl = y0[S.i(f"m__{prefix}")]
        T_cyl = y0[S.i(f"T__{prefix}")]
        V_cyl, _, _ = cyl.kinematics.volume_dVdtheta_x(y0[S.i("theta")])
        p_cyl = gas.p_from_mTV(m_cyl, T_cyl, V_cyl)
        assert math.isclose(p_cyl, cfg.initial.p0_pa, rel_tol=1e-12)
        assert math.isclose(T_cyl, cfg.initial.T0_K, rel_tol=0.0, abs_tol=1e-12)



def test_disabled_throttle_uses_manifold_boundary_values_in_signals(cfg):
    throttle = replace(cfg.throttle, enabled=False)
    cfg2 = replace(cfg, throttle=throttle)
    S, ctx, model, t_span, y0 = ModelBuilder(cfg2).build()

    _ = model.rhs(t_span[0], y0.copy())

    assert math.isclose(ctx.signals["p_upstream_throttle_pa"], cfg.manifolds.p_int_pa, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(ctx.signals["T_upstream_throttle_K"], cfg.manifolds.T_int_K, rel_tol=0.0, abs_tol=1e-12)
