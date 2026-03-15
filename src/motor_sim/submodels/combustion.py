from __future__ import annotations

import math


def _cyclic_progress(theta_deg: float, start_deg: float, duration_deg: float, cycle_deg: float) -> float:
    """Return normalized progress in [0,1] along a cyclic interval."""
    dur = max(float(duration_deg), 1e-12)
    rel = (float(theta_deg) - float(start_deg)) % float(cycle_deg)
    return max(0.0, min(1.0, rel / dur))


def cyclic_signed_offset(angle_deg: float, ref_deg: float, cycle_deg: float) -> float:
    half = 0.5 * float(cycle_deg)
    return float(((float(angle_deg) - float(ref_deg) + half) % float(cycle_deg)) - half)


def wiebe_x50(wiebe_a: float, wiebe_m: float) -> float:
    a = max(float(wiebe_a), 1e-12)
    m = float(wiebe_m)
    return float((math.log(2.0) / a) ** (1.0 / (m + 1.0)))


def soc_from_ca50(ca50_deg: float, duration_deg: float, wiebe_a: float, wiebe_m: float, cycle_deg: float) -> float:
    return float((float(ca50_deg) - wiebe_x50(wiebe_a, wiebe_m) * float(duration_deg)) % float(cycle_deg))


def released_energy_from_lambda(
    m_air_kg: float,
    lambda_value: float,
    fuel_afr_stoich_kg_air_per_kg_fuel: float,
    fuel_lhv_J_per_kg: float,
    combustion_efficiency: float = 1.0,
) -> float:
    lam = max(float(lambda_value), 1e-9)
    afr_st = max(float(fuel_afr_stoich_kg_air_per_kg_fuel), 1e-12)
    lhv = max(float(fuel_lhv_J_per_kg), 0.0)
    eta = max(0.0, min(float(combustion_efficiency), 1.0))
    m_air = max(float(m_air_kg), 0.0)
    m_fuel = m_air / (lam * afr_st)
    return float(m_fuel * lhv * eta)


def combustion_angle_summary(comb_cfg: dict, cycle_deg: float, zot_deg: float) -> dict:
    cycle_deg = float(cycle_deg)
    zot_deg = float(zot_deg)
    duration_deg = float(comb_cfg.get("duration_deg", 40.0))
    wiebe_a = float(comb_cfg.get("wiebe_a", 5.0))
    wiebe_m = float(comb_cfg.get("wiebe_m", 2.0))

    ca50_rel = None
    ca50_abs = None
    if "ca50_rel_zuend_ot_deg" in comb_cfg:
        ca50_rel = float(comb_cfg.get("ca50_rel_zuend_ot_deg", 0.0))
        ca50_abs = float((zot_deg + ca50_rel) % cycle_deg)
        soc_abs = soc_from_ca50(ca50_abs, duration_deg, wiebe_a, wiebe_m, cycle_deg)
        soc_rel = cyclic_signed_offset(soc_abs, zot_deg, cycle_deg)
    elif "soc_rel_zuend_ot_deg" in comb_cfg:
        soc_rel = float(comb_cfg.get("soc_rel_zuend_ot_deg", 0.0))
        soc_abs = float((zot_deg + soc_rel) % cycle_deg)
    else:
        legacy_ref_deg = 360.0 if cycle_deg >= 720.0 else 0.0
        soc_abs = float(comb_cfg.get("soc_deg", legacy_ref_deg)) % cycle_deg
        soc_rel = cyclic_signed_offset(soc_abs, zot_deg, cycle_deg)

    if ca50_abs is None:
        ca50_abs = float((soc_abs + wiebe_x50(wiebe_a, wiebe_m) * duration_deg) % cycle_deg)
        ca50_rel = cyclic_signed_offset(ca50_abs, zot_deg, cycle_deg)

    return {
        "zot_deg": zot_deg,
        "duration_deg": duration_deg,
        "wiebe_a": wiebe_a,
        "wiebe_m": wiebe_m,
        "soc_abs_deg": float(soc_abs),
        "soc_rel_zuend_ot_deg": float(soc_rel),
        "ca50_abs_deg": float(ca50_abs),
        "ca50_rel_zuend_ot_deg": float(ca50_rel),
    }


def combustion_q_total_J(comb_cfg: dict, m_air_kg: float) -> float:
    mode = str(comb_cfg.get("heat_input_mode", "manual")).strip().lower()
    if mode == "lambda":
        return released_energy_from_lambda(
            m_air_kg=m_air_kg,
            lambda_value=float(comb_cfg.get("lambda", 1.0)),
            fuel_afr_stoich_kg_air_per_kg_fuel=float(comb_cfg.get("fuel_afr_stoich_kg_air_per_kg_fuel", 14.7)),
            fuel_lhv_J_per_kg=float(comb_cfg.get("fuel_lhv_J_per_kg", 42.5e6)),
            combustion_efficiency=float(comb_cfg.get("combustion_efficiency", 1.0)),
        )
    return float(comb_cfg.get("q_total_J_per_cycle", 0.0))


def wiebe_heat_release(theta_deg: float, cycle_deg: float, soc_deg: float, duration_deg: float,
                       q_total_J_per_cycle: float, wiebe_a: float, wiebe_m: float) -> tuple[float, float, float]:
    """Return (qdot_per_rad, x_burned, dq_dtheta) for a cyclic Wiebe heat-release law.

    qdot_per_rad is dQ/dtheta in J/rad.
    x_burned and dq_dtheta are dimensionless burned fraction and J/deg respectively.
    """
    if float(q_total_J_per_cycle) == 0.0 or float(duration_deg) <= 0.0:
        return 0.0, 0.0, 0.0

    rel = (float(theta_deg) - float(soc_deg)) % float(cycle_deg)
    if rel < 0.0 or rel > float(duration_deg):
        if rel > float(duration_deg):
            return 0.0, (1.0 if rel < float(cycle_deg) - 1e-12 else 0.0), 0.0
        return 0.0, 0.0, 0.0

    x = _cyclic_progress(theta_deg, soc_deg, duration_deg, cycle_deg)
    a = float(wiebe_a)
    m = float(wiebe_m)
    xb = 1.0 - math.exp(-a * max(x, 0.0) ** (m + 1.0))
    dxb_dx = a * (m + 1.0) * max(x, 0.0) ** m * math.exp(-a * max(x, 0.0) ** (m + 1.0))
    dxb_ddeg = dxb_dx / max(float(duration_deg), 1e-12)
    dq_ddeg = float(q_total_J_per_cycle) * dxb_ddeg
    dq_drad = dq_ddeg * 180.0 / math.pi
    return dq_drad, xb, dq_ddeg


class Combustion:
    def contribute(self, t, y, ctx, aux, dy):
        pass
