from dataclasses import dataclass
from typing import Any

from motor_sim.components.liner_model import LinerModel, PistonModel, HeadModel

@dataclass
class UserCylinder:
    name: str
    engine: Any
    gas: Any
    kinematics: Any
    piston: PistonModel
    liner: LinerModel
    head: HeadModel
    area_provider: Any | None = None
    connections: dict | None = None
    notes: str = ""
    crank_angle_offset_deg: float = 0.0
    runner_cfg: dict | None = None

    def eval_geometry(self, theta_rad: float) -> dict:
        theta_local = float(theta_rad) + float(self.crank_angle_offset_deg) * 3.141592653589793 / 180.0
        V, dV_dtheta, x = self.kinematics.volume_dVdtheta_x(theta_local)
        return {
            "V_m3": float(V),
            "dV_dtheta_m3_per_rad": float(dV_dtheta),
            "x_from_tdc_m": float(x),
            "theta_local_deg": float(theta_local * 180.0 / 3.141592653589793),
            "A_piston_m2": float(self.piston.area_m2),
            "A_head_m2": float(self.head.area_m2),
            "A_liner_wet_m2": float(self.liner.wetted_area_m2(x)),
            "A_liner_total_m2": float(self.liner.total_swept_wall_area_m2()),
            "T_wall_piston_K": float(self.piston.crown_temperature_K),
            "T_wall_head_K": float(self.head.wall_temperature_K),
            "T_wall_liner_K": float(self.liner.wall_temperature_K),
        }

    def eval_ports_or_valves(self, theta_deg: float, aux: dict, ctx: Any):
        if self.area_provider is None:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        return self.area_provider.eval(theta_deg, aux, ctx)

def build_user_cylinder(name: str, engine: Any, gas: Any, kinematics: Any, area_provider: Any | None = None, connections: dict | None = None, notes: str = "", piston_cfg: dict | None = None, liner_cfg: dict | None = None, head_cfg: dict | None = None, crank_angle_offset_deg: float = 0.0, runner_cfg: dict | None = None) -> UserCylinder:
    bore_m = float(getattr(kinematics, "bore"))
    stroke_m = float(getattr(kinematics, "stroke"))
    piston_cfg = piston_cfg or {}
    liner_cfg = liner_cfg or {}
    head_cfg = head_cfg or {}
    return UserCylinder(
        name=name,
        engine=engine,
        gas=gas,
        kinematics=kinematics,
        piston=PistonModel(
            bore_m=bore_m,
            area_scale=float(piston_cfg.get("area_scale", 1.0)),
            crown_temperature_K=float(piston_cfg.get("crown_temperature_K", 520.0)),
        ),
        liner=LinerModel(
            bore_m=bore_m,
            stroke_m=stroke_m,
            area_scale=float(liner_cfg.get("area_scale", 1.0)),
            wall_temperature_K=float(liner_cfg.get("wall_temperature_K", 430.0)),
        ),
        head=HeadModel(
            bore_m=bore_m,
            area_scale=float(head_cfg.get("area_scale", 1.0)),
            wall_temperature_K=float(head_cfg.get("wall_temperature_K", 480.0)),
        ),
        area_provider=area_provider,
        connections=connections or {},
        notes=notes,
        crank_angle_offset_deg=float(crank_angle_offset_deg),
        runner_cfg=runner_cfg or {},
    )
