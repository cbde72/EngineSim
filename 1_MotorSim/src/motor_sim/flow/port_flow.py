from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import math

from motor_sim.flow.nozzle_choked import mdot_nozzle, mdot_nozzle_signed
from motor_sim.flow.simple_orifice import mdot_orifice

PortDirection = Literal['to_cylinder', 'from_cylinder']

@dataclass(frozen=True)
class PortDefinition:
    """Unified description of a gas-exchange port used by the solver.

    Parameters
    ----------
    name:
        Human-readable port name (e.g. ``intake`` or ``exhaust``).
    direction:
        Sign convention relative to the cylinder.
        ``to_cylinder`` means positive signed flow enters the cylinder.
        ``from_cylinder`` means negative signed flow leaves the cylinder.
    area_eff_m2:
        Effective hydraulic area already including alphaK/alphaV logic.
    cd:
        Discharge coefficient applied by the flow model.
    area_geom_m2:
        Optional geometric reference area for diagnostics.
    alpha_v:
        Optional valve flow coefficient based on valve-seat area.
    lift_m:
        Optional lift used for diagnostics.
    """

    name: str
    direction: PortDirection
    area_eff_m2: float
    cd: float
    area_geom_m2: float = 0.0
    alpha_v: float | None = None
    lift_m: float | None = None


def signed_port_mdot(
    port: PortDefinition,
    p_cyl: float,
    T_cyl: float,
    p_other: float,
    T_other: float,
    flow_model: str,
    gamma: float,
    R: float,
    min_temperature_K: float = 1.0e-9,
) -> float:
    """Return signed mass flow in cylinder sign convention.

    Positive means *into* the cylinder, negative means *out of* the cylinder.
    """
    A = max(float(port.area_eff_m2), 0.0)
    Cd = max(float(port.cd), 0.0)
    if A <= 0.0 or Cd <= 0.0:
        return 0.0

    if str(flow_model) == 'nozzle_choked':
        if port.direction == 'to_cylinder':
            return mdot_nozzle_signed(Cd, A, p_other, T_other, p_cyl, T_cyl, gamma, R)
        return -mdot_nozzle_signed(Cd, A, p_cyl, T_cyl, p_other, T_other, gamma, R)

    # simple_orifice fallback with sign support
    if p_other >= p_cyl:
        p_up, T_up, p_dn = p_other, T_other, p_cyl
        sign_to_cyl = +1.0
    else:
        p_up, T_up, p_dn = p_cyl, T_cyl, p_other
        sign_to_cyl = -1.0
    rho = p_up / (R * max(T_up, min_temperature_K))
    dp = max(p_up - p_dn, 0.0)
    mdot_mag = mdot_orifice(Cd, A, rho, dp)
    signed_to_cyl = sign_to_cyl * mdot_mag
    if port.direction == 'to_cylinder':
        return signed_to_cyl
    return -signed_to_cyl


def enthalpy_from_signed_flow(mdot_signed_to_cyl: float, cp: float, T_cyl: float, T_other: float) -> float:
    """Return enthalpy term ``mdot*h`` in cylinder sign convention.

    Positive signed flow uses the *other-side* temperature because fluid enters the
    cylinder from there. Negative signed flow uses cylinder temperature because fluid
    leaves the cylinder carrying cylinder enthalpy.
    """
    if mdot_signed_to_cyl >= 0.0:
        return mdot_signed_to_cyl * cp * T_other
    return mdot_signed_to_cyl * cp * T_cyl


def flow_direction_label(mdot_signed_to_cyl: float, tol: float = 1.0e-15) -> str:
    if mdot_signed_to_cyl > tol:
        return 'into_cylinder'
    if mdot_signed_to_cyl < -tol:
        return 'out_of_cylinder'
    return 'stagnant'
