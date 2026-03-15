import numpy as np
from scipy.integrate import solve_ivp

class SciPyIntegrator:
    def __init__(self, model, t0, t_end, y0, cfg, dt_out):
        self.model = model
        self.t0 = float(t0)
        self.t_end = float(t_end)
        self.y0 = np.array(y0, dtype=float)
        self.cfg = cfg
        self.dt_out = float(dt_out)

    def run(self):
        n = int(np.floor((self.t_end - self.t0) / self.dt_out)) + 1
        t_eval = self.t0 + np.arange(n) * self.dt_out
        t_eval[-1] = min(t_eval[-1], self.t_end)

        sol = solve_ivp(
            fun=self.model.rhs,
            t_span=(self.t0, self.t_end),
            y0=self.y0,
            t_eval=t_eval,
            method=self.cfg.method,
            rtol=self.cfg.rtol,
            atol=self.cfg.atol,
            max_step=self.cfg.max_step_s,
        )
        if not sol.success:
            raise RuntimeError(f"Integration failed: {sol.message}")
        return sol.t, sol.y

class RK4FixedIntegrator:
    def __init__(self, model, t0, t_end, y0, dt_internal, dt_out):
        self.model = model
        self.t0 = float(t0)
        self.t_end = float(t_end)
        self.y0 = np.array(y0, dtype=float)
        self.dt = float(dt_internal)
        self.dt_out = float(dt_out)

    def run(self, on_sample=None):
        n_out = int(np.floor((self.t_end - self.t0) / self.dt_out)) + 1
        t_out = self.t0 + np.arange(n_out) * self.dt_out
        t_out[-1] = min(t_out[-1], self.t_end)

        y = self.y0.copy()
        Y = np.zeros((len(y), n_out), dtype=float)

        t = self.t0

        def step_rk4(t, y, h):
            f = self.model.rhs
            k1 = f(t, y)
            k2 = f(t + 0.5*h, y + 0.5*h*k1)
            k3 = f(t + 0.5*h, y + 0.5*h*k2)
            k4 = f(t + h, y + h*k3)
            return y + (h/6.0)*(k1 + 2*k2 + 2*k3 + k4)

        for out_i in range(n_out):
            next_out = t_out[out_i]
            while t + 1e-15 < next_out:
                h = min(self.dt, next_out - t)
                y = step_rk4(t, y, h)
                t += h
            Y[:, out_i] = y
            if on_sample is not None:
                on_sample(t, y, out_i)

        return t_out, Y
