from __future__ import annotations

import math

import numpy as np

from motor_sim.post.phase_logic import ideal_phase_array, ideal_phase_scalar, reference_points
from motor_sim.submodels.combustion import (
    combustion_angle_summary,
    combustion_q_total_J,
    cyclic_signed_offset,
    released_energy_from_lambda,
    soc_from_ca50,
    wiebe_heat_release,
    wiebe_x50,
)


def test_reference_points_for_4t_modes_and_offset_are_consistent():
    refs_fire = reference_points(cycle_deg=720.0, angle_ref_mode='FIRE_TDC')
    refs_gx = reference_points(cycle_deg=720.0, angle_ref_mode='GAS_EXCHANGE_TDC')

    assert refs_fire['firing_tdc_deg'] == 0.0
    assert refs_fire['gas_exchange_tdc_deg'] == 360.0
    assert refs_gx['gas_exchange_tdc_deg'] == 0.0
    assert refs_gx['firing_tdc_deg'] == 360.0

    refs_off = reference_points(cycle_deg=720.0, angle_ref_mode='FIRE_TDC', crank_angle_offset_deg=90.0)
    assert math.isclose(refs_off['firing_tdc_deg'], 630.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(refs_off['power_bdc_deg'], 90.0, rel_tol=0.0, abs_tol=1e-12)


def test_ideal_phase_scalar_and_array_match_expected_4t_sequence():
    thetas = np.array([0.0, 200.0, 400.0, 600.0])
    phases = ideal_phase_array(thetas, cycle_deg=720.0, angle_ref_mode='FIRE_TDC')
    assert phases.tolist() == ['arbeiten', 'ausschieben', 'ansaugen', 'verdichten']

    for theta_deg, expected in zip(thetas, phases.tolist()):
        assert ideal_phase_scalar(theta_deg, cycle_deg=720.0, angle_ref_mode='FIRE_TDC') == expected


def test_cyclic_signed_offset_stays_within_half_cycle():
    cycle_deg = 720.0
    for angle_deg in [-1440.0, -10.0, 0.0, 15.0, 719.0, 1440.0]:
        off = cyclic_signed_offset(angle_deg, ref_deg=5.0, cycle_deg=cycle_deg)
        assert -0.5 * cycle_deg <= off < 0.5 * cycle_deg


def test_combustion_angle_summary_ca50_and_soc_modes_are_self_consistent():
    cycle_deg = 720.0
    zot_deg = 0.0
    base = {
        'duration_deg': 50.0,
        'wiebe_a': 5.0,
        'wiebe_m': 2.0,
    }

    cfg_ca50 = dict(base, ca50_rel_zuend_ot_deg=8.0)
    summary_ca50 = combustion_angle_summary(cfg_ca50, cycle_deg=cycle_deg, zot_deg=zot_deg)

    expected_soc = soc_from_ca50(
        ca50_deg=summary_ca50['ca50_abs_deg'],
        duration_deg=base['duration_deg'],
        wiebe_a=base['wiebe_a'],
        wiebe_m=base['wiebe_m'],
        cycle_deg=cycle_deg,
    )
    assert math.isclose(summary_ca50['soc_abs_deg'], expected_soc, rel_tol=0.0, abs_tol=1e-12)

    cfg_soc = dict(base, soc_rel_zuend_ot_deg=-5.0)
    summary_soc = combustion_angle_summary(cfg_soc, cycle_deg=cycle_deg, zot_deg=zot_deg)
    expected_ca50 = (summary_soc['soc_abs_deg'] + wiebe_x50(base['wiebe_a'], base['wiebe_m']) * base['duration_deg']) % cycle_deg
    assert math.isclose(summary_soc['ca50_abs_deg'], expected_ca50, rel_tol=0.0, abs_tol=1e-12)


def test_combustion_q_total_manual_and_lambda_modes_are_consistent():
    m_air_kg = 0.0008
    cfg_manual = {'heat_input_mode': 'manual', 'q_total_J_per_cycle': 321.0}
    assert combustion_q_total_J(cfg_manual, m_air_kg=m_air_kg) == 321.0

    cfg_lambda = {
        'heat_input_mode': 'lambda',
        'lambda': 1.2,
        'fuel_afr_stoich_kg_air_per_kg_fuel': 14.7,
        'fuel_lhv_J_per_kg': 42.5e6,
        'combustion_efficiency': 0.95,
    }
    expected = released_energy_from_lambda(
        m_air_kg=m_air_kg,
        lambda_value=cfg_lambda['lambda'],
        fuel_afr_stoich_kg_air_per_kg_fuel=cfg_lambda['fuel_afr_stoich_kg_air_per_kg_fuel'],
        fuel_lhv_J_per_kg=cfg_lambda['fuel_lhv_J_per_kg'],
        combustion_efficiency=cfg_lambda['combustion_efficiency'],
    )
    assert math.isclose(combustion_q_total_J(cfg_lambda, m_air_kg=m_air_kg), expected, rel_tol=1e-12)


def test_wiebe_heat_release_is_zero_outside_window_and_positive_inside():
    q_total = 500.0
    qdot0, xb0, dq0 = wiebe_heat_release(
        theta_deg=55.0,
        cycle_deg=720.0,
        soc_deg=10.0,
        duration_deg=40.0,
        q_total_J_per_cycle=q_total,
        wiebe_a=5.0,
        wiebe_m=2.0,
    )
    assert qdot0 == 0.0
    assert xb0 == 1.0
    assert dq0 == 0.0

    qdot1, xb1, dq1 = wiebe_heat_release(
        theta_deg=25.0,
        cycle_deg=720.0,
        soc_deg=10.0,
        duration_deg=40.0,
        q_total_J_per_cycle=q_total,
        wiebe_a=5.0,
        wiebe_m=2.0,
    )
    assert qdot1 > 0.0
    assert 0.0 < xb1 < 1.0
    assert dq1 > 0.0
