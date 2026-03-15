from __future__ import annotations

import math

from motor_sim.flow.nozzle_choked import mdot_nozzle, mdot_nozzle_signed
from motor_sim.flow.port_flow import PortDefinition, enthalpy_from_signed_flow, flow_direction_label, signed_port_mdot
from motor_sim.flow.runner_model import area_from_diameter, effective_area, hydraulic_phi
from motor_sim.flow.simple_orifice import mdot_orifice
from motor_sim.flow.throttle_model import throttle_area
from motor_sim.gas.idealgas import IdealGas


def test_ideal_gas_properties_and_pressure_equation_are_consistent():
    gas = IdealGas(R=287.0, cp=1005.0)
    assert math.isclose(gas.cv, 718.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(gas.gamma, gas.cp / gas.cv, rel_tol=1e-12)

    p = gas.p_from_mTV(m=0.002, T=320.0, V=0.001)
    assert math.isclose(p, 0.002 * 287.0 * 320.0 / 0.001, rel_tol=1e-12)


def test_throttle_area_and_runner_effective_area_obey_basic_bounds():
    d = 0.04
    amax = area_from_diameter(d)
    assert math.isclose(throttle_area(diameter_m=d, position=0.5), 0.5 * amax, rel_tol=1e-12)
    assert throttle_area(diameter_m=d, position=-1.0) == 0.0
    assert throttle_area(diameter_m=d, position=2.0) == amax

    phi = hydraulic_phi(length_m=0.3, diameter_m=0.03, zeta_local=1.0, friction_factor=0.03)
    a_eff, phi_eff = effective_area(area_geom_m2=amax, length_m=0.3, diameter_m=0.03, zeta_local=1.0, friction_factor=0.03)
    assert 0.0 < phi <= 1.0
    assert math.isclose(phi_eff, phi, rel_tol=1e-12)
    assert 0.0 < a_eff <= amax


def test_nozzle_and_orifice_primitives_return_expected_sign_and_zero_limits():
    gamma = 1.4
    R = 287.0
    md = mdot_nozzle(Cd=0.8, A=1e-4, p_up=2e5, T_up=300.0, p_down=1e5, gamma=gamma, R=R)
    assert md > 0.0
    assert mdot_nozzle(Cd=0.8, A=0.0, p_up=2e5, T_up=300.0, p_down=1e5, gamma=gamma, R=R) == 0.0

    md_signed = mdot_nozzle_signed(Cd=0.8, A=1e-4, p1=2e5, T1=300.0, p2=1e5, T2=320.0, gamma=gamma, R=R)
    md_signed_rev = mdot_nozzle_signed(Cd=0.8, A=1e-4, p1=1e5, T1=320.0, p2=2e5, T2=300.0, gamma=gamma, R=R)
    assert md_signed > 0.0
    assert md_signed_rev < 0.0
    assert math.isclose(md_signed, -md_signed_rev, rel_tol=1e-12)

    md_or = mdot_orifice(Cd=0.7, A=1e-4, rho_up=1.2, dp=5e4)
    assert md_or > 0.0
    assert mdot_orifice(Cd=0.7, A=1e-4, rho_up=1.2, dp=0.0) == 0.0


def test_port_flow_sign_convention_enthalpy_and_labels_are_consistent():
    gamma = 1.4
    R = 287.0
    cp = 1005.0

    intake = PortDefinition(name='intake', direction='to_cylinder', area_eff_m2=1e-4, cd=0.8)
    exhaust = PortDefinition(name='exhaust', direction='from_cylinder', area_eff_m2=1e-4, cd=0.8)

    md_int = signed_port_mdot(
        intake,
        p_cyl=1.0e5,
        T_cyl=650.0,
        p_other=2.0e5,
        T_other=300.0,
        flow_model='nozzle_choked',
        gamma=gamma,
        R=R,
    )
    assert md_int > 0.0
    assert flow_direction_label(md_int) == 'into_cylinder'
    assert math.isclose(enthalpy_from_signed_flow(md_int, cp, T_cyl=650.0, T_other=300.0), md_int * cp * 300.0, rel_tol=1e-12)

    md_ex = signed_port_mdot(
        exhaust,
        p_cyl=2.0e5,
        T_cyl=700.0,
        p_other=1.0e5,
        T_other=500.0,
        flow_model='nozzle_choked',
        gamma=gamma,
        R=R,
    )
    assert md_ex < 0.0
    assert flow_direction_label(md_ex) == 'out_of_cylinder'
    assert math.isclose(enthalpy_from_signed_flow(md_ex, cp, T_cyl=700.0, T_other=500.0), md_ex * cp * 700.0, rel_tol=1e-12)
