from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp



def test_short_integration_runs_and_stays_finite(built_model):
    model = built_model["model"]
    y0 = built_model["y0"]
    t0, t_end = built_model["t_span"]

    short_end = min(t_end, t0 + max(1e-4, 0.01 * (t_end - t0)))

    sol = solve_ivp(
        fun=model.rhs,
        t_span=(t0, short_end),
        y0=y0.copy(),
        method="RK45",
        rtol=1e-8,
        atol=1e-10,
        max_step=max((short_end - t0) / 50.0, 1e-6),
    )

    assert sol.success, sol.message
    assert sol.y.shape[0] == y0.shape[0]
    assert np.all(np.isfinite(sol.y))
    assert np.all(np.isfinite(sol.t))
