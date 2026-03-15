from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .phase_logic import reference_points
from motor_sim.submodels.combustion import combustion_angle_summary, combustion_q_total_J


def _round1(x):
    return round(float(x), 1)


@dataclass
class EnergySummary:
    E_flow_in_J: float
    E_flow_out_J: float
    E_piston_J: float
    E_combustion_J: float
    E_wall_J: float
    E_generator_proxy_J: float
    delta_U_J: float
    closure_residual_J: float
    closure_relative_pct: float
    U0_J: float
    U1_J: float

    def to_dict(self) -> dict:
        return {
            "E_flow_in_J": _round1(self.E_flow_in_J),
            "E_flow_out_J": _round1(self.E_flow_out_J),
            "E_piston_J": _round1(self.E_piston_J),
            "E_combustion_J": _round1(self.E_combustion_J),
            "E_wall_J": _round1(self.E_wall_J),
            "E_generator_proxy_J": _round1(self.E_generator_proxy_J),
            "delta_U_J": _round1(self.delta_U_J),
            "closure_residual_J": _round1(self.closure_residual_J),
            "closure_relative_pct": _round1(self.closure_relative_pct),
            "U0_J": _round1(self.U0_J),
            "U1_J": _round1(self.U1_J),
        }


def trapezoid_integral(t_s, y):
    t = np.asarray(t_s, dtype=float)
    yy = np.asarray(y, dtype=float)
    if len(t) < 2 or len(yy) < 2:
        return 0.0
    return float(np.trapezoid(yy, t))


class EnergyTermModel(ABC):
    name: str

    @abstractmethod
    def enabled(self, cfg_energy: dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def compute_energy_J(self, df: pd.DataFrame, cfg_energy: dict, gas_R: float, gas_cp: float, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> float:
        raise NotImplementedError


class CombustionWiebeEnergyModel(EnergyTermModel):
    name = "combustion"

    def enabled(self, cfg_energy: dict) -> bool:
        return bool(cfg_energy.get("combustion", {}).get("enabled", False))

    def compute_energy_J(self, df: pd.DataFrame, cfg_energy: dict, gas_R: float, gas_cp: float, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> float:
        cfg = cfg_energy.get("combustion", {})
        if len(df) == 0:
            return 0.0
        theta_src = "theta_local_deg" if "theta_local_deg" in df.columns else "theta_deg"
        cycle_deg = 720.0 if float(np.nanmax(np.asarray(df[theta_src], dtype=float))) > 400.0 else 360.0
        zot = float(reference_points(cycle_deg=cycle_deg, angle_ref_mode=angle_ref_mode)["firing_tdc_deg"])
        comb_angles = combustion_angle_summary(cfg, cycle_deg=cycle_deg, zot_deg=zot)
        soc = float(comb_angles["soc_abs_deg"])
        dur = max(1e-9, float(comb_angles["duration_deg"]))
        a = float(comb_angles["wiebe_a"])
        m_w = float(comb_angles["wiebe_m"])
        theta = np.asarray(df[theta_src], dtype=float)
        theta_mod = np.mod(theta, cycle_deg)
        rel = np.mod(theta_mod - soc, cycle_deg)
        active = rel <= dur
        if not np.any(active):
            return 0.0
        if str(cfg.get("heat_input_mode", "manual")).strip().lower() == "lambda":
            idx_ref = int(np.where(active)[0][0])
            m_air_kg = float(np.asarray(df["m_cyl_kg"], dtype=float)[idx_ref]) if "m_cyl_kg" in df.columns else 0.0
            q_total = combustion_q_total_J(cfg, m_air_kg=m_air_kg)
        else:
            q_total = float(cfg.get("q_total_J_per_cycle", 0.0))
        if q_total == 0.0:
            return 0.0
        x = np.clip(rel / dur, 0.0, 1.0)
        dx_dtheta = np.zeros_like(theta_mod, dtype=float)
        dx_dtheta[active] = (
            a * (m_w + 1.0) * np.power(np.maximum(x[active], 0.0), m_w) *
            np.exp(-a * np.power(np.maximum(x[active], 0.0), m_w + 1.0))
        ) / dur
        t = np.asarray(df["t_s"], dtype=float)
        if len(t) < 2:
            return 0.0
        dtheta_dt = np.gradient(theta, t)
        qdot = dx_dtheta * dtheta_dt * q_total
        return trapezoid_integral(t, qdot)


class WallHeatLumpedEnergyModel(EnergyTermModel):
    name = "wall_heat"

    def enabled(self, cfg_energy: dict) -> bool:
        return bool(cfg_energy.get("wall_heat", {}).get("enabled", False))

    def compute_energy_J(self, df: pd.DataFrame, cfg_energy: dict, gas_R: float, gas_cp: float, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> float:
        cfg = cfg_energy.get("wall_heat", {})
        if len(df) == 0:
            return 0.0
        t = np.asarray(df["t_s"], dtype=float)
        T_cyl = np.asarray(df["T_cyl_K"], dtype=float) if "T_cyl_K" in df.columns else np.zeros(len(t))
        A_p = np.asarray(df["A_piston_m2"], dtype=float) if "A_piston_m2" in df.columns else np.zeros(len(t))
        A_h = np.asarray(df["A_head_m2"], dtype=float) if "A_head_m2" in df.columns else np.zeros(len(t))
        A_l = np.asarray(df["A_liner_wet_m2"], dtype=float) if "A_liner_wet_m2" in df.columns else np.zeros(len(t))
        T_wp = np.asarray(df["T_wall_piston_K"], dtype=float) if "T_wall_piston_K" in df.columns else np.zeros(len(t))
        T_wh = np.asarray(df["T_wall_head_K"], dtype=float) if "T_wall_head_K" in df.columns else np.zeros(len(t))
        T_wl = np.asarray(df["T_wall_liner_K"], dtype=float) if "T_wall_liner_K" in df.columns else np.zeros(len(t))
        hp = float(cfg.get("h_piston_W_m2K", 150.0))
        hh = float(cfg.get("h_head_W_m2K", 180.0))
        hl = float(cfg.get("h_liner_W_m2K", 130.0))
        qdot_wall = hp * A_p * (T_cyl - T_wp) + hh * A_h * (T_cyl - T_wh) + hl * A_l * (T_cyl - T_wl)
        return trapezoid_integral(t, qdot_wall)


class GeneratorProxyEnergyModel(EnergyTermModel):
    name = "generator"

    def enabled(self, cfg_energy: dict) -> bool:
        return bool(cfg_energy.get("generator", {}).get("enabled", False))

    def compute_energy_J(self, df: pd.DataFrame, cfg_energy: dict, gas_R: float, gas_cp: float, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> float:
        cfg = cfg_energy.get("generator", {})
        if len(df) == 0:
            return 0.0
        t = np.asarray(df["t_s"], dtype=float)
        p = np.asarray(df["p_cyl_pa"], dtype=float) if "p_cyl_pa" in df.columns else np.zeros(len(t))
        V = np.asarray(df["V_m3"], dtype=float) if "V_m3" in df.columns else np.zeros(len(t))
        eta = float(cfg.get("eta_mech_to_electric", 0.9))
        positive_only = bool(cfg.get("positive_work_only", True))
        if len(t) < 2:
            return 0.0
        dV_dt = np.gradient(V, t)
        pwr = p * dV_dt
        if positive_only:
            pwr = np.maximum(pwr, 0.0)
        return trapezoid_integral(t, eta * pwr)


def energy_balance_from_dataframe(df: pd.DataFrame, gas_R: float, gas_cp: float, cfg_energy: dict | None = None, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> EnergySummary:
    if len(df) == 0:
        return EnergySummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    cfg_energy = dict(cfg_energy or {})
    cv = float(gas_cp) - float(gas_R)
    t = df["t_s"].to_numpy(dtype=float)
    mdot_in = df["mdot_in_kg_s"].to_numpy(dtype=float) if "mdot_in_kg_s" in df.columns else 0.0 * t
    mdot_out = df["mdot_out_kg_s"].to_numpy(dtype=float) if "mdot_out_kg_s" in df.columns else 0.0 * t
    T_in = df["T_int_plenum_K"].to_numpy(dtype=float) if "T_int_plenum_K" in df.columns else (
        df["T_upstream_throttle_K"].to_numpy(dtype=float) if "T_upstream_throttle_K" in df.columns else 300.0 + 0.0 * t
    )
    T_cyl = df["T_cyl_K"].to_numpy(dtype=float) if "T_cyl_K" in df.columns else 300.0 + 0.0 * t
    p = df["p_cyl_pa"].to_numpy(dtype=float) if "p_cyl_pa" in df.columns else 0.0 * t
    V = df["V_m3"].to_numpy(dtype=float) if "V_m3" in df.columns else 0.0 * t
    m = df["m_cyl_kg"].to_numpy(dtype=float) if "m_cyl_kg" in df.columns else 0.0 * t

    h_in = float(gas_cp) * T_in
    h_out = float(gas_cp) * T_cyl
    u = cv * m * T_cyl
    dV_dt = np.gradient(V, t) if len(t) >= 2 else np.zeros_like(V)
    p_dVdt = p * dV_dt

    E_flow_in = trapezoid_integral(t, mdot_in * h_in)
    E_flow_out = trapezoid_integral(t, mdot_out * h_out)
    E_piston = trapezoid_integral(t, p_dVdt)
    U0 = float(u[0]) if len(u) else 0.0
    U1 = float(u[-1]) if len(u) else 0.0
    delta_U = U1 - U0

    models = [CombustionWiebeEnergyModel(), WallHeatLumpedEnergyModel(), GeneratorProxyEnergyModel()]
    vals = {m.name: (m.compute_energy_J(df, cfg_energy, gas_R, gas_cp, angle_ref_mode=angle_ref_mode, crank_angle_offset_deg=crank_angle_offset_deg) if m.enabled(cfg_energy) else 0.0) for m in models}
    E_comb = float(vals.get("combustion", 0.0))
    E_wall = float(vals.get("wall_heat", 0.0))
    E_gen = float(vals.get("generator", 0.0))

    residual = delta_U - (E_flow_in - E_flow_out - E_piston + E_comb - E_wall)
    denom = max(1e-9, abs(E_flow_in) + abs(E_flow_out) + abs(E_piston) + abs(E_comb) + abs(E_wall) + abs(delta_U))
    rel_pct = 100.0 * residual / denom

    return EnergySummary(
        E_flow_in_J=E_flow_in,
        E_flow_out_J=E_flow_out,
        E_piston_J=E_piston,
        E_combustion_J=E_comb,
        E_wall_J=E_wall,
        E_generator_proxy_J=E_gen,
        delta_U_J=delta_U,
        closure_residual_J=residual,
        closure_relative_pct=rel_pct,
        U0_J=U0,
        U1_J=U1,
    )


def write_energy_summary(summary: EnergySummary, out_dir: Path, filename: str = "energy_balance_summary.json") -> Path:
    out_path = Path(out_dir) / filename
    out_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")
    return out_path
