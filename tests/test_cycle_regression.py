from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

try:
    import pytest_html
    extras = pytest_html.extras
except Exception:  # pragma: no cover
    extras = None

from tests.dashboard_helpers import build_dashboard_html


@dataclass
class CycleSummary:
    theta_deg: np.ndarray
    p_pa: np.ndarray
    V_m3: np.ndarray
    mdot_in: np.ndarray
    mdot_out: np.ndarray
    qdot_comb_W: np.ndarray
    p_int_plenum_pa: np.ndarray
    p_ex_plenum_pa: np.ndarray
    pmax_pa: float
    theta_pmax_deg: float
    pmin_pa: float
    Vmin_m3: float
    Vmax_m3: float
    work_ind_J: float


def _make_eval_grid(ctx, steps_per_cycle: int = 361):
    cycle_deg = float(ctx.engine.cycle_deg)
    cycle_rad = math.radians(cycle_deg)
    omega = float(ctx.engine.omega_rad_s)

    t0 = 0.0
    t1 = cycle_rad / omega
    t_eval = np.linspace(t0, t1, steps_per_cycle)
    theta_eval_deg = np.degrees(omega * t_eval)
    return t0, t1, t_eval, theta_eval_deg


def _integrate_one_cycle(model, y0, ctx, steps_per_cycle: int = 361):
    t0, t1, t_eval, theta_eval_deg = _make_eval_grid(ctx, steps_per_cycle=steps_per_cycle)

    sol = solve_ivp(
        fun=model.rhs,
        t_span=(t0, t1),
        y0=np.array(y0, dtype=float, copy=True),
        t_eval=t_eval,
        method="RK45",
        rtol=1e-8,
        atol=1e-10,
        max_step=(t1 - t0) / 1000.0,
    )
    assert sol.success, sol.message

    return sol, theta_eval_deg


def _extract_cycle_summary(model, ctx, sol, theta_eval_deg):
    p = []
    V = []
    mdot_in = []
    mdot_out = []
    qdot = []
    p_int = []
    p_ex = []

    for k in range(sol.y.shape[1]):
        _ = model.rhs(float(sol.t[k]), sol.y[:, k].copy())
        sig = dict(ctx.signals)

        p.append(float(sig.get("p", np.nan)))
        V.append(float(sig.get("V", np.nan)))
        mdot_in.append(float(sig.get("mdot_in", np.nan)))
        mdot_out.append(float(sig.get("mdot_out", np.nan)))
        qdot.append(float(sig.get("qdot_combustion_W", 0.0)))
        p_int.append(float(sig.get("p_int_plenum_pa", np.nan)))
        p_ex.append(float(sig.get("p_ex_plenum_pa", np.nan)))

    p = np.asarray(p)
    V = np.asarray(V)
    mdot_in = np.asarray(mdot_in)
    mdot_out = np.asarray(mdot_out)
    qdot = np.asarray(qdot)
    p_int = np.asarray(p_int)
    p_ex = np.asarray(p_ex)

    idx_pmax = int(np.nanargmax(p))
    work_ind = float(np.trapezoid(p, V))

    return CycleSummary(
        theta_deg=np.asarray(theta_eval_deg),
        p_pa=p,
        V_m3=V,
        mdot_in=mdot_in,
        mdot_out=mdot_out,
        qdot_comb_W=qdot,
        p_int_plenum_pa=p_int,
        p_ex_plenum_pa=p_ex,
        pmax_pa=float(np.nanmax(p)),
        theta_pmax_deg=float(theta_eval_deg[idx_pmax]),
        pmin_pa=float(np.nanmin(p)),
        Vmin_m3=float(np.nanmin(V)),
        Vmax_m3=float(np.nanmax(V)),
        work_ind_J=work_ind,
    )


def _summary_to_dict(summary: CycleSummary) -> dict:
    return {
        "theta_deg": summary.theta_deg,
        "p_pa": summary.p_pa,
        "V_m3": summary.V_m3,
        "mdot_in": summary.mdot_in,
        "mdot_out": summary.mdot_out,
        "qdot_comb_W": summary.qdot_comb_W,
        "p_int_plenum_pa": summary.p_int_plenum_pa,
        "p_ex_plenum_pa": summary.p_ex_plenum_pa,
    }


def _run_cycle_from_fixture(built_model, steps_per_cycle: int = 361):
    model = built_model["model"]
    ctx = built_model["ctx"]
    y0 = built_model["y0"]
    sol, theta_eval_deg = _integrate_one_cycle(model, y0, ctx, steps_per_cycle=steps_per_cycle)
    return _extract_cycle_summary(model, ctx, sol, theta_eval_deg)


def test_complete_cycle_smoke(built_model, request):
    summary = _run_cycle_from_fixture(built_model)

    if extras is not None:
        request.node._html_extras = [
            extras.html(
                build_dashboard_html(
                    cur=_summary_to_dict(summary),
                    ref=None,
                    title="Engineering Test Dashboard - Cycle Smoke Test",
                )
            )
        ]

    assert len(summary.theta_deg) == 361
    assert np.all(np.isfinite(summary.p_pa))
    assert np.all(np.isfinite(summary.V_m3))
    assert np.all(np.isfinite(summary.p_int_plenum_pa))
    assert np.all(np.isfinite(summary.p_ex_plenum_pa))

    assert summary.Vmin_m3 > 0.0
    assert summary.Vmax_m3 > summary.Vmin_m3
    assert summary.pmax_pa > summary.pmin_pa
    assert summary.pmax_pa > 1.0e4
    assert summary.pmax_pa < 5.0e8
    assert summary.theta_pmax_deg >= summary.theta_deg.min()
    assert summary.theta_pmax_deg <= summary.theta_deg.max()


def test_complete_cycle_repeatability(cfg):
    from motor_sim.core.builder import ModelBuilder

    _S1, ctx1, model1, _t_span1, y01 = ModelBuilder(cfg).build()
    sol1, theta_eval_deg1 = _integrate_one_cycle(model1, y01, ctx1, steps_per_cycle=361)
    summary1 = _extract_cycle_summary(model1, ctx1, sol1, theta_eval_deg1)

    _S2, ctx2, model2, _t_span2, y02 = ModelBuilder(cfg).build()
    sol2, theta_eval_deg2 = _integrate_one_cycle(model2, y02, ctx2, steps_per_cycle=361)
    summary2 = _extract_cycle_summary(model2, ctx2, sol2, theta_eval_deg2)

    np.testing.assert_allclose(summary1.theta_deg, summary2.theta_deg, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(summary1.p_pa, summary2.p_pa, rtol=1e-9, atol=1e-6)
    np.testing.assert_allclose(summary1.V_m3, summary2.V_m3, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(summary1.mdot_in, summary2.mdot_in, rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(summary1.mdot_out, summary2.mdot_out, rtol=1e-9, atol=1e-9)
    np.testing.assert_allclose(summary1.qdot_comb_W, summary2.qdot_comb_W, rtol=1e-9, atol=1e-6)


def test_complete_cycle_key_metrics_are_plausible(built_model):
    summary = _run_cycle_from_fixture(built_model)

    assert summary.pmax_pa > 2.0e5
    assert summary.pmax_pa < 3.0e8
    assert summary.Vmin_m3 > 0.0
    assert summary.Vmax_m3 > summary.Vmin_m3
    assert math.isfinite(summary.work_ind_J)
    assert abs(summary.work_ind_J) > 1e-6
    assert np.all(np.isfinite(summary.qdot_comb_W))


def test_cycle_matches_reference_curve(built_model, request, reference_file):
    ref_path = reference_file
    assert ref_path.exists(), f"Missing reference file: {ref_path}"

    ref_npz = np.load(ref_path)
    ref = {
        "theta_deg": ref_npz["theta_deg"],
        "p_pa": ref_npz["p_pa"],
        "V_m3": ref_npz["V_m3"],
        "mdot_in": ref_npz["mdot_in"],
        "mdot_out": ref_npz["mdot_out"],
        "qdot_comb_W": ref_npz["qdot_comb_W"],
        "p_int_plenum_pa": ref_npz["p_int_plenum_pa"],
        "p_ex_plenum_pa": ref_npz["p_ex_plenum_pa"],
    }
    cur_summary = _run_cycle_from_fixture(built_model)
    cur = _summary_to_dict(cur_summary)

    if extras is not None:
        request.node._html_extras = [
            extras.html(
                build_dashboard_html(
                    cur=cur,
                    ref=ref,
                    title="Engineering Test Dashboard - Cycle Regression",
                )
            )
        ]

    np.testing.assert_allclose(cur_summary.theta_deg, ref["theta_deg"], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(cur_summary.V_m3, ref["V_m3"], rtol=1e-10, atol=1e-14)
    np.testing.assert_allclose(cur_summary.p_pa, ref["p_pa"], rtol=5e-4, atol=50.0)
    np.testing.assert_allclose(cur_summary.mdot_in, ref["mdot_in"], rtol=2e-3, atol=1e-6)
    np.testing.assert_allclose(cur_summary.mdot_out, ref["mdot_out"], rtol=2e-3, atol=1e-6)
    np.testing.assert_allclose(cur_summary.qdot_comb_W, ref["qdot_comb_W"], rtol=2e-3, atol=1e-3)
    np.testing.assert_allclose(cur_summary.p_int_plenum_pa, ref["p_int_plenum_pa"], rtol=1e-4, atol=20.0)
    np.testing.assert_allclose(cur_summary.p_ex_plenum_pa, ref["p_ex_plenum_pa"], rtol=1e-4, atol=20.0)


def test_cycle_key_metrics_match_reference(built_model, reference_file):
    ref = np.load(reference_file)
    cur = _run_cycle_from_fixture(built_model)

    p_ref = ref["p_pa"]
    p_cur = cur.p_pa
    th = cur.theta_deg

    iref = int(np.argmax(p_ref))
    icur = int(np.argmax(p_cur))

    pmax_ref = float(p_ref[iref])
    pmax_cur = float(p_cur[icur])
    theta_pmax_ref = float(th[iref])
    theta_pmax_cur = float(th[icur])

    np.testing.assert_allclose(pmax_cur, pmax_ref, rtol=5e-4, atol=100.0)
    np.testing.assert_allclose(theta_pmax_cur, theta_pmax_ref, rtol=0.0, atol=1.0)

    work_ref = float(np.trapezoid(ref["p_pa"], ref["V_m3"]))
    work_cur = float(np.trapezoid(cur.p_pa, cur.V_m3))
    np.testing.assert_allclose(work_cur, work_ref, rtol=2e-3, atol=1e-3)
