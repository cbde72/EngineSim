from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pandas as pd

from motor_sim.post.cycle_convergence import compute_cycle_metrics
from motor_sim.post.energy_balance import energy_balance_from_dataframe
from motor_sim.post.state_decode import (
    _detect_prefixes,
    detect_prefixes,
    gas_cv,
    internal_energy_from_mass_temp,
    scalar_temperature_from_rowlike,
    temperature_from_mass_energy,
    temperature_series_from_columns,
)


def test_detect_prefixes_returns_unique_sorted_prefixes():
    df = pd.DataFrame(
        {
            "cylB__m_rin_kg_state": [1.0],
            "cylA__U_rin_J_state": [2.0],
            "cylB__U_rex_J_state": [3.0],
            "noise": [4.0],
            "cylA__m_rex_kg_state": [5.0],
        }
    )

    suffixes = (
        "__m_rin_kg_state",
        "__U_rin_J_state",
        "__m_rex_kg_state",
        "__U_rex_J_state",
    )

    assert detect_prefixes(df, suffixes) == ["cylA", "cylB"]
    assert _detect_prefixes(df, suffixes) == ["cylA", "cylB"]



def test_temperature_helpers_roundtrip_mass_temp_energy():
    gas_R = 287.0
    gas_cp = 1005.0
    mass = 0.0025
    temp = 640.0

    U = internal_energy_from_mass_temp(mass, temp, gas_R, gas_cp)
    T_back = temperature_from_mass_energy(mass, U, gas_R, gas_cp)

    assert math.isclose(T_back, temp, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(gas_cv(gas_R, gas_cp), gas_cp - gas_R, rel_tol=0.0, abs_tol=0.0)



def test_temperature_series_and_scalar_fallback_to_energy_when_temperature_missing():
    gas_R = 287.0
    gas_cp = 1005.0
    cv = gas_cp - gas_R
    masses = np.array([0.001, 0.0015, 0.002])
    temps = np.array([400.0, 500.0, 600.0])
    energies = masses * cv * temps

    df = pd.DataFrame({"m": masses, "U": energies})
    series = temperature_series_from_columns(
        df,
        mass_col="m",
        temp_col="T_missing",
        energy_col="U",
        gas_R=gas_R,
        gas_cp=gas_cp,
        default_K=123.0,
    )

    np.testing.assert_allclose(series, temps, rtol=1e-12, atol=1e-12)

    row = df.iloc[-1]
    T_scalar = scalar_temperature_from_rowlike(
        row,
        mass_key="m",
        temp_key="T_missing",
        energy_key="U",
        gas_R=gas_R,
        gas_cp=gas_cp,
        default_K=123.0,
    )
    assert math.isclose(T_scalar, temps[-1], rel_tol=1e-12, abs_tol=1e-12)



def test_compute_cycle_metrics_supports_mu_only_runner_and_plenum_states():
    gas_R = 287.0
    gas_cp = 1005.0
    cv = gas_cp - gas_R

    row = {
        "m_cyl_kg": 0.002,
        "U_cyl_J_state": 0.002 * cv * 650.0,
        "m_int_plenum_kg": 0.01,
        "U_int_plenum_J": 0.01 * cv * 300.0,
        "m_ex_plenum_kg": 0.012,
        "U_ex_plenum_J": 0.012 * cv * 520.0,
        "cylA__m_rin_kg_state": 0.001,
        "cylA__U_rin_J_state": 0.001 * cv * 310.0,
        "cylA__m_rex_kg_state": 0.0012,
        "cylA__U_rex_J_state": 0.0012 * cv * 700.0,
        "cylB__m_rin_kg_state": 0.0011,
        "cylB__U_rin_J_state": 0.0011 * cv * 315.0,
        "cylB__m_rex_kg_state": 0.0013,
        "cylB__U_rex_J_state": 0.0013 * cv * 705.0,
        "theta_deg": 0.0,
        "V_m3": 1.0e-4,
        "p_cyl_pa": 2.0e5,
        "t_s": 0.0,
    }
    df = pd.DataFrame([row, {**row, "theta_deg": 720.0, "t_s": 0.02, "V_m3": 1.1e-4, "p_cyl_pa": 1.9e5}])

    ctx = SimpleNamespace(
        gas=SimpleNamespace(R=gas_R, cp=gas_cp),
        engine=SimpleNamespace(displacement_m3=5.0e-4),
    )
    conv_cfg = SimpleNamespace(monitored_states=None)

    metrics = compute_cycle_metrics(df, y_end=None, ctx=ctx, S=None, conv_cfg=conv_cfg)

    expected_plenum_temp = np.mean([300.0, 520.0])
    expected_runner_temp = np.mean([310.0, 700.0, 315.0, 705.0])
    expected_runner_mass = 0.001 + 0.0012 + 0.0011 + 0.0013

    assert math.isclose(metrics["temp"], 650.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(metrics["plenum_temp"], expected_plenum_temp, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(metrics["runner_temp"], expected_runner_temp, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(metrics["runner_mass"], expected_runner_mass, rel_tol=1e-12, abs_tol=1e-12)



def test_energy_balance_uses_internal_energy_directly_when_temperature_columns_are_absent():
    gas_R = 287.0
    gas_cp = 1005.0
    cv = gas_cp - gas_R
    m = 0.002
    U0 = m * cv * 500.0
    U1 = m * cv * 550.0

    df = pd.DataFrame(
        {
            "t_s": [0.0, 0.01],
            "m_cyl_kg": [m, m],
            "U_cyl_J_state": [U0, U1],
            "m_int_plenum_kg": [0.01, 0.01],
            "U_int_plenum_J": [0.01 * cv * 300.0, 0.01 * cv * 300.0],
            "p_cyl_pa": [0.0, 0.0],
            "V_m3": [1.0e-4, 1.0e-4],
            "mdot_in_kg_s": [0.0, 0.0],
            "mdot_out_kg_s": [0.0, 0.0],
        }
    )

    summary = energy_balance_from_dataframe(df, gas_R=gas_R, gas_cp=gas_cp, cfg_energy={})

    assert math.isclose(summary.U0_J, U0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(summary.U1_J, U1, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(summary.delta_U_J, U1 - U0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(summary.E_flow_in_J, 0.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(summary.E_flow_out_J, 0.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(summary.E_piston_J, 0.0, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(summary.closure_residual_J, U1 - U0, rel_tol=1e-12, abs_tol=1e-12)
