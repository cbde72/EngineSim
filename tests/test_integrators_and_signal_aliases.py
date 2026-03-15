from __future__ import annotations

import math

import numpy as np

from motor_sim.core.integrator import RK4FixedIntegrator, SciPyIntegrator



def test_scipy_integrator_runs_and_returns_expected_grid(built_model):
    model = built_model["model"]
    cfg = built_model["cfg"]
    y0 = built_model["y0"]
    t0, t_end = built_model["t_span"]

    dt_out = max(cfg.simulation.output.dt_out_s, 1e-5)
    short_end = min(t_end, t0 + 3.0 * dt_out)

    integ = SciPyIntegrator(
        model=model,
        t0=t0,
        t_end=short_end,
        y0=y0.copy(),
        cfg=cfg.simulation.integrator,
        dt_out=dt_out,
    )
    t, Y = integ.run()

    assert t.ndim == 1
    assert Y.ndim == 2
    assert Y.shape[0] == y0.shape[0]
    assert Y.shape[1] == t.shape[0]
    assert np.all(np.isfinite(t))
    assert np.all(np.isfinite(Y))
    np.testing.assert_allclose(Y[:, 0], y0, rtol=0.0, atol=0.0)



def test_rk4_fixed_integrator_runs_and_calls_sampler(built_model):
    model = built_model["model"]
    cfg = built_model["cfg"]
    y0 = built_model["y0"]
    t0, t_end = built_model["t_span"]

    dt_out = max(cfg.simulation.output.dt_out_s, 1e-5)
    dt_internal = max(min(cfg.simulation.integrator.dt_internal_s, dt_out / 2.0), 1e-6)
    short_end = min(t_end, t0 + 3.0 * dt_out)

    calls: list[tuple[float, int]] = []

    integ = RK4FixedIntegrator(
        model=model,
        t0=t0,
        t_end=short_end,
        y0=y0.copy(),
        dt_internal=dt_internal,
        dt_out=dt_out,
    )
    t, Y = integ.run(on_sample=lambda ts, y, i: calls.append((ts, i)))

    assert Y.shape[0] == y0.shape[0]
    assert Y.shape[1] == t.shape[0]
    assert len(calls) == t.shape[0]
    assert calls[0][1] == 0
    assert calls[-1][1] == t.shape[0] - 1
    assert np.all(np.isfinite(t))
    assert np.all(np.isfinite(Y))
    np.testing.assert_allclose(Y[:, 0], y0, rtol=0.0, atol=0.0)



def test_active_cylinder_alias_signals_match_active_cylinder_signals(built_model):
    ctx = built_model["ctx"]
    model = built_model["model"]
    y0 = built_model["y0"]
    t0 = built_model["t_span"][0]

    _ = model.rhs(t0, y0.copy())

    active = ctx.cylinder.name
    mapping = {
        "theta_local_deg": f"{active}__theta_local_deg",
        "V": f"{active}__V_m3",
        "x": f"{active}__x_m",
        "p": f"{active}__p_cyl_pa",
        "mdot_in": f"{active}__mdot_intake_to_cyl_kg_s",
        "mdot_out": f"{active}__mdot_exhaust_to_cyl_kg_s",
        "A_in": f"{active}__A_in_m2",
        "A_ex": f"{active}__A_ex_m2",
        "qdot_combustion_W": f"{active}__qdot_combustion_W",
        "xb_combustion": f"{active}__xb_combustion",
    }

    for alias, specific in mapping.items():
        assert alias in ctx.signals
        assert specific in ctx.signals
        assert math.isclose(float(ctx.signals[alias]), float(ctx.signals[specific]), rel_tol=0.0, abs_tol=1e-12)
