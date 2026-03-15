from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import replace

import numpy as np

from motor_sim.core.builder import ModelBuilder


EXTREME_THETA_DEG = [
    -720.0,
    -360.0,
    -359.999,
    -180.001,
    -180.0,
    -179.999,
    -0.001,
    0.0,
    0.001,
    179.999,
    180.0,
    180.001,
    359.999,
    360.0,
    360.001,
    720.0,
]


def _build_from_cfg(cfg):
    S, ctx, model, t_span, y0 = ModelBuilder(cfg).build()
    return S, ctx, model, t_span, y0



def test_rhs_stays_finite_at_extreme_crank_angles(built_model):
    S = built_model["S"]
    model = built_model["model"]
    ctx = built_model["ctx"]
    y0 = built_model["y0"]
    t0 = built_model["t_span"][0]

    for theta_deg in EXTREME_THETA_DEG:
        y = y0.copy()
        y[S.i("theta")] = math.radians(theta_deg)
        dy = model.rhs(t0, y)

        assert np.all(np.isfinite(dy)), f"Non-finite rhs at theta={theta_deg} deg"
        for cyl in ctx.cylinders:
            assert math.isfinite(float(ctx.signals[f"{cyl.name}__V_m3"]))
            assert math.isfinite(float(ctx.signals[f"{cyl.name}__p_cyl_pa"]))
            assert math.isfinite(float(ctx.signals[f"{cyl.name}__A_in_m2"]))
            assert math.isfinite(float(ctx.signals[f"{cyl.name}__A_ex_m2"]))



def test_rhs_remains_finite_with_tiny_volume_and_mass_floors(cfg):
    tiny_intake = replace(cfg.plena.intake, volume_m3=1e-15)
    tiny_exhaust = replace(cfg.plena.exhaust, volume_m3=1e-15)
    plena = replace(cfg.plena, intake=tiny_intake, exhaust=tiny_exhaust)

    uc0 = cfg.user_cylinders[0]
    runners = replace(
        uc0.runners,
        intake=replace(uc0.runners.intake, volume_m3=1e-15),
        exhaust=replace(uc0.runners.exhaust, volume_m3=1e-15),
    )
    uc0_small = replace(uc0, runners=runners)
    user_cylinders = [uc0_small, *cfg.user_cylinders[1:]]

    cfg2 = replace(
        cfg,
        plena=plena,
        user_cylinders=user_cylinders,
        numerics={"min_volume_m3": 1e-12, "min_runner_volume_m3": 1e-11, "min_mass_kg": 1e-12},
    )

    S, ctx, model, t_span, y0 = _build_from_cfg(cfg2)

    y = y0.copy()
    for name in S.names:
        if name.startswith("m_"):
            y[S.i(name)] = 5e-13
        elif name.startswith("T_"):
            y[S.i(name)] = 250.0

    dy = model.rhs(t_span[0], y)

    assert np.all(np.isfinite(dy))
    numeric_signal_values = [v for v in ctx.signals.values() if isinstance(v, (int, float))]
    assert np.all(np.isfinite(numeric_signal_values))



def test_fully_closed_system_has_zero_mass_exchange_rates(cfg):
    ge = replace(cfg.gasexchange, enabled=False)
    throttle = replace(cfg.throttle, enabled=False)
    cfg2 = replace(
        cfg,
        gasexchange=ge,
        throttle=throttle,
        links={"plenum_feed_area_m2": 0.0, "plenum_feed_cd": 0.0, "runner_to_plenum_area_m2": 0.0},
    )

    S, ctx, model, t_span, y0 = _build_from_cfg(cfg2)
    dy = model.rhs(t_span[0], y0.copy())

    mass_state_names = [n for n in S.names if n.startswith("m_")]
    for name in mass_state_names:
        assert math.isclose(float(dy[S.i(name)]), 0.0, rel_tol=0.0, abs_tol=1e-15), name

    assert math.isclose(float(ctx.signals["mdot_feed_int_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(float(ctx.signals["mdot_discharge_ex_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)
    for cyl in ctx.cylinders:
        assert math.isclose(float(ctx.signals[f"{cyl.name}__mdot_plenum_to_rin_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)
        assert math.isclose(float(ctx.signals[f"{cyl.name}__mdot_rin_to_cyl_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)
        assert math.isclose(float(ctx.signals[f"{cyl.name}__mdot_cyl_to_rex_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)
        assert math.isclose(float(ctx.signals[f"{cyl.name}__mdot_rex_to_plenum_kg_s"]), 0.0, rel_tol=0.0, abs_tol=1e-15)



def test_rhs_is_repeatable_even_for_near_floor_state(cfg):
    cfg2 = replace(
        cfg,
        numerics={"min_volume_m3": 1e-12, "min_runner_volume_m3": 1e-12, "min_mass_kg": 1e-12},
    )
    S, ctx, model, t_span, y0 = _build_from_cfg(cfg2)

    y = y0.copy()
    y[S.i("theta")] = math.radians(359.999)
    for name in S.names:
        if name.startswith("m_"):
            y[S.i(name)] = 2e-12
        elif name.startswith("T_"):
            y[S.i(name)] = 280.0

    dy1 = model.rhs(t_span[0], y.copy())
    sig1 = dict(ctx.signals)
    dy2 = model.rhs(t_span[0], y.copy())
    sig2 = dict(ctx.signals)

    np.testing.assert_allclose(dy1, dy2, rtol=0.0, atol=0.0)
    assert sig1.keys() == sig2.keys()
    for key in sig1:
        v1 = sig1[key]
        v2 = sig2[key]
        if isinstance(v1, str) or isinstance(v2, str):
            assert v1 == v2
        else:
            assert math.isclose(float(v1), float(v2), rel_tol=0.0, abs_tol=0.0), key
