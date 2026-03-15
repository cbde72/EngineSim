from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from motor_sim.core.builder import ModelBuilder


def test_rhs_is_repeatable_for_same_input_state(built_model):
    model = built_model['model']
    y0 = built_model['y0']
    t0 = built_model['t_span'][0]

    dy1 = model.rhs(t0, y0.copy())
    sig1 = dict(built_model['ctx'].signals)
    dy2 = model.rhs(t0, y0.copy())
    sig2 = dict(built_model['ctx'].signals)

    np.testing.assert_allclose(dy1, dy2, rtol=0.0, atol=0.0)
    assert sig1.keys() == sig2.keys()
    for key in sig1:
        v1 = sig1[key]
        v2 = sig2[key]
        if isinstance(v1, str) or isinstance(v2, str):
            assert v1 == v2
        else:
            assert math.isclose(float(v1), float(v2), rel_tol=0.0, abs_tol=0.0)


def test_disabled_gasexchange_keeps_rhs_finite_and_zeroes_port_areas(cfg):
    ge = replace(cfg.gasexchange, enabled=False)
    cfg2 = replace(cfg, gasexchange=ge)
    S, ctx, model, t_span, y0 = ModelBuilder(cfg2).build()

    dy = model.rhs(t_span[0], y0.copy())

    assert np.all(np.isfinite(dy))
    for cyl in ctx.cylinders:
        assert ctx.signals[f'{cyl.name}__A_in_m2'] == 0.0
        assert ctx.signals[f'{cyl.name}__A_ex_m2'] == 0.0
        assert ctx.signals[f'{cyl.name}__mdot_intake_to_cyl_kg_s'] == 0.0
        assert ctx.signals[f'{cyl.name}__mdot_exhaust_to_cyl_kg_s'] == 0.0


def test_two_enabled_cylinders_show_expected_theta_offset(cfg):
    base = cfg.user_cylinders[0]
    cyl2 = replace(
        cfg.user_cylinders[1],
        enabled=True,
        crank_angle_offset_deg=base.crank_angle_offset_deg + 360.0,
    )
    cfg2 = replace(cfg, user_cylinders=[base, cyl2], active_user_cylinder=cyl2.name)
    S, ctx, model, t_span, y0 = ModelBuilder(cfg2).build()

    _ = model.rhs(t_span[0], y0.copy())

    theta1 = ctx.signals[f'{base.name}__theta_local_deg']
    theta2 = ctx.signals[f'{cyl2.name}__theta_local_deg']
    assert math.isclose(theta2 - theta1, 360.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(ctx.signals['theta_local_deg'], theta2, rel_tol=0.0, abs_tol=1e-9)
