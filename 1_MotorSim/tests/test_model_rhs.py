from __future__ import annotations

import math

import numpy as np


CORE_SIGNAL_KEYS = [
    "theta_deg",
    "theta_local_deg",
    "p",
    "V",
    "x",
    "mdot_in",
    "mdot_out",
    "p_int_plenum_pa",
    "T_int_plenum_K",
    "m_int_plenum_kg",
    "p_ex_plenum_pa",
    "T_ex_plenum_K",
    "m_ex_plenum_kg",
    "mdot_feed_int_kg_s",
    "mdot_discharge_ex_kg_s",
]


def _perturb_state(S, y0):
    y = np.array(y0, dtype=float, copy=True)
    y[S.i("theta")] += math.radians(23.0)
    for name in S.names:
        if name.startswith("m_"):
            y[S.i(name)] *= 1.01
        elif name.startswith("T_"):
            y[S.i(name)] *= 0.998
    return y



def test_rhs_initial_state_is_finite_and_shape_consistent(built_model):
    S = built_model["S"]
    ctx = built_model["ctx"]
    model = built_model["model"]
    y0 = built_model["y0"]
    t0 = built_model["t_span"][0]

    dy = model.rhs(t0, y0.copy())

    assert dy.shape == y0.shape
    assert np.all(np.isfinite(dy))
    assert math.isclose(dy[S.i("theta")], ctx.engine.omega_rad_s, rel_tol=0.0, abs_tol=1e-15)



def test_rhs_perturbed_state_is_finite(built_model):
    S = built_model["S"]
    model = built_model["model"]
    y = _perturb_state(S, built_model["y0"])
    t0 = built_model["t_span"][0]

    dy = model.rhs(t0, y)

    assert dy.shape == y.shape
    assert np.all(np.isfinite(dy))



def test_rhs_populates_core_signals_and_per_cylinder_signals(built_model):
    ctx = built_model["ctx"]
    model = built_model["model"]
    y0 = built_model["y0"]
    t0 = built_model["t_span"][0]

    _ = model.rhs(t0, y0.copy())

    for key in CORE_SIGNAL_KEYS:
        assert key in ctx.signals, f"Missing core signal: {key}"

    for cyl in ctx.cylinders:
        prefix = cyl.name
        required = [
            f"{prefix}__theta_local_deg",
            f"{prefix}__V_m3",
            f"{prefix}__x_m",
            f"{prefix}__p_cyl_pa",
            f"{prefix}__m_cyl_kg",
            f"{prefix}__T_cyl_K",
            f"{prefix}__mdot_intake_to_cyl_kg_s",
            f"{prefix}__mdot_exhaust_to_cyl_kg_s",
            f"{prefix}__p_rin_pa",
            f"{prefix}__T_rin_K",
            f"{prefix}__p_rex_pa",
            f"{prefix}__T_rex_K",
        ]
        for key in required:
            assert key in ctx.signals, f"Missing cylinder signal: {key}"
            value = ctx.signals[key]
            if isinstance(value, (int, float)):
                assert math.isfinite(float(value)), f"Non-finite cylinder signal: {key}={value}"
