import json
from dataclasses import dataclass
from typing import Optional, Literal, Any, Dict

from motor_sim.paths import resolve_input_file

IntegratorType = Literal["rk4_fixed", "scipy"]
FlowModel = Literal["nozzle_choked", "simple_orifice"]
GasExchangeMode = Literal["valves", "ports", "slots"]

@dataclass(frozen=True)
class EngineCfg:
    cycle_type: str
    rpm: Optional[float]
    freq_hz: Optional[float]
    bore_m: float
    stroke_m: float
    conrod_m: float
    compression_ratio: float

@dataclass(frozen=True)
class GasCfg:
    R_J_per_kgK: float
    cp_J_per_kgK: float

@dataclass(frozen=True)
class ManifoldCfg:
    p_int_pa: float
    T_int_K: float
    p_ex_pa: float
    T_ex_K: float

@dataclass(frozen=True)
class InitialCfg:
    p0_pa: float
    T0_K: float

@dataclass(frozen=True)
class IntegratorCfg:
    type: IntegratorType
    method: str
    rtol: float
    atol: float
    max_step_s: float
    dt_internal_s: float

@dataclass(frozen=True)
class OutputGridCfg:
    dt_out_s: float
    dtheta_out_deg: float

@dataclass(frozen=True)
class LivePlotCfg:
    enabled: bool
    every_n_out: int
    window_s: float

@dataclass(frozen=True)
class AngleReferenceCfg:
    mode: str
    plot_theta_min_deg: float
    plot_theta_max_deg: float

@dataclass(frozen=True)
class CycleConvergenceCfg:
    enabled: bool
    rel_tol_mass: float
    rel_tol_temp: float
    abs_tol_mass_kg: float
    abs_tol_temp_K: float
    required_consecutive_cycles: int
    min_cycles_before_check: int
    stop_when_converged: bool
    verbose: bool
    monitored_states: list[str]
    rel_tol_other: float
    abs_tol_other: float

@dataclass(frozen=True)
class SimulationCfg:
    t0_s: float
    theta0_deg: float
    n_cycles_store: int
    n_cycles_compute: int
    integrator: IntegratorCfg
    output: OutputGridCfg
    live_plot: LivePlotCfg
    cycle_convergence: CycleConvergenceCfg

@dataclass(frozen=True)
class ValvesCfg:
    lift_file: str
    alphak_file: str
    d_in_m: float
    d_ex_m: float
    count_in: int
    count_ex: int
    A_in_port_max_m2: float
    A_ex_port_max_m2: float
    intake_open: Dict[str, Any]
    exhaust_open: Dict[str, Any]
    scaling: Dict[str, Any]
    lift_angle_basis: str
    cam_to_crank_ratio: float
    effective_lift_threshold_mm: float

@dataclass(frozen=True)
class PortsCfg:
    area_file: str
    alphak_file: str

@dataclass(frozen=True)
class SlotGeomCfg:
    width_m: float
    height_m: float
    count: int
    offset_from_ut_m: float
    roof: Dict[str, Any]
    alphak_file: str | None
    channel: Dict[str, Any]

@dataclass(frozen=True)
class SlotsCfg:
    alphak_file: str
    intake: SlotGeomCfg
    exhaust: SlotGeomCfg
    intake_groups: list[SlotGeomCfg]
    exhaust_groups: list[SlotGeomCfg]

@dataclass(frozen=True)
class GasExchangeCfg:
    enabled: bool
    mode: GasExchangeMode
    flow_model: FlowModel
    valves: ValvesCfg
    ports: PortsCfg
    slots: SlotsCfg

@dataclass(frozen=True)
class OutputFilesCfg:
    out_dir: str
    csv_name: str
    plot_name: str

@dataclass(frozen=True)
class UserCylinderZoneCfg:
    area_scale: float
    wall_temperature_K: float

@dataclass(frozen=True)
class UserCylinderPistonCfg:
    area_scale: float
    crown_temperature_K: float

@dataclass(frozen=True)
class UserCylinderConnectionsCfg:
    intake_name: str
    exhaust_name: str

@dataclass(frozen=True)
class RunnerSideCfg:
    enabled: bool
    length_m: float
    diameter_m: float
    volume_m3: float
    zeta_local: float
    friction_factor: float
    wall_temperature_K: float

@dataclass(frozen=True)
class RunnerPairCfg:
    intake: RunnerSideCfg
    exhaust: RunnerSideCfg

@dataclass(frozen=True)
class UserCylinderCfg:
    name: str
    enabled: bool
    crank_angle_offset_deg: float
    actuation_source: str
    notes: str
    connections: UserCylinderConnectionsCfg
    runners: RunnerPairCfg
    piston: UserCylinderPistonCfg
    liner: UserCylinderZoneCfg
    head: UserCylinderZoneCfg

@dataclass(frozen=True)
class PlenumSideCfg:
    volume_m3: float
    p0_pa: float
    T0_K: float

@dataclass(frozen=True)
class PlenaCfg:
    enabled: bool
    intake: PlenumSideCfg
    exhaust: PlenumSideCfg

@dataclass(frozen=True)
class ThrottleCfg:
    enabled: bool
    diameter_m: float
    cd: float
    position: float
    position_mode: str
    A_max_m2: float
    T_upstream_K: float
    p_upstream_pa: float

@dataclass(frozen=True)
class SlotEventsCfg:
    enabled: bool
    area_threshold_m2: float
    per_group: bool
    per_group_blowdown: bool
    plot_groups: bool

@dataclass(frozen=True)
class GroupContribCfg:
    enabled: bool
    area_threshold_m2: float

@dataclass(frozen=True)
class GroupFlowModelCfg:
    enabled: bool
    mode: str

@dataclass(frozen=True)
class PostprocessCfg:
    slot_events: SlotEventsCfg
    group_contributions: GroupContribCfg
    group_flow_model: GroupFlowModelCfg

@dataclass(frozen=True)
class Config:
    case_name: str
    engine: EngineCfg
    gas: GasCfg
    manifolds: ManifoldCfg
    initial: InitialCfg
    simulation: SimulationCfg
    gasexchange: GasExchangeCfg
    output_files: OutputFilesCfg
    user_cylinders: list[UserCylinderCfg]
    active_user_cylinder: str
    plena: PlenaCfg
    throttle: ThrottleCfg
    energy_models: dict
    angle_reference: AngleReferenceCfg
    postprocess: PostprocessCfg
    numerics: dict
    links: dict
    thresholds: dict
    plot_style: dict

def _mk_slot_geom(d):
    return SlotGeomCfg(
        float(d.get("width_m", 0.0)),
        float(d.get("height_m", 0.0)),
        int(d.get("count", 0)),
        float(d.get("offset_from_ut_m", 0.0)),
        dict(d.get("roof", {})),
        str(d["alphak_file"]) if d.get("alphak_file") else None,
        dict(d.get("channel", {})),
    )

def _mk_runner_side(d, default_T):
    return RunnerSideCfg(
        enabled=bool(d.get("enabled", True)),
        length_m=float(d.get("length_m", 0.25)),
        diameter_m=float(d.get("diameter_m", 0.035)),
        volume_m3=float(d.get("volume_m3", 0.00024)),
        zeta_local=float(d.get("zeta_local", 1.2)),
        friction_factor=float(d.get("friction_factor", 0.03)),
        wall_temperature_K=float(d.get("wall_temperature_K", default_T)),
    )

def _mk_user_cylinder(d: Dict[str, Any]) -> UserCylinderCfg:
    runners = d.get("runners", {})
    return UserCylinderCfg(
        name=str(d.get("name", "user_cylinder_1")),
        enabled=bool(d.get("enabled", True)),
        crank_angle_offset_deg=float(d.get("crank_angle_offset_deg", 0.0)),
        actuation_source=str(d.get("actuation_source", "auto")),
        notes=str(d.get("notes", "")),
        connections=UserCylinderConnectionsCfg(
            intake_name=str(d.get("connections", {}).get("intake_name", "intake_manifold_1")),
            exhaust_name=str(d.get("connections", {}).get("exhaust_name", "exhaust_manifold_1")),
        ),
        runners=RunnerPairCfg(
            intake=_mk_runner_side(runners.get("intake", {}), 320.0),
            exhaust=_mk_runner_side(runners.get("exhaust", {}), 650.0),
        ),
        piston=UserCylinderPistonCfg(
            area_scale=float(d.get("piston", {}).get("area_scale", 1.0)),
            crown_temperature_K=float(d.get("piston", {}).get("crown_temperature_K", 520.0)),
        ),
        liner=UserCylinderZoneCfg(
            area_scale=float(d.get("liner", {}).get("area_scale", 1.0)),
            wall_temperature_K=float(d.get("liner", {}).get("wall_temperature_K", 430.0)),
        ),
        head=UserCylinderZoneCfg(
            area_scale=float(d.get("head", {}).get("area_scale", 1.0)),
            wall_temperature_K=float(d.get("head", {}).get("wall_temperature_K", 480.0)),
        ),
    )

def load_config(path: str) -> Config:
    path = str(path)
    raw = json.loads(open(path, "r", encoding="utf-8").read())

    def _resolve_file(value: str | None) -> str | None:
        if value is None or str(value).strip() == '':
            return value
        return str(resolve_input_file(path, value))

    gx_raw = raw.get('gasexchange', {})
    if isinstance(gx_raw.get('valves'), dict):
        gx_raw['valves']['lift_file'] = _resolve_file(gx_raw['valves'].get('lift_file'))
        gx_raw['valves']['alphak_file'] = _resolve_file(gx_raw['valves'].get('alphak_file'))
    if isinstance(gx_raw.get('ports'), dict):
        gx_raw['ports']['area_file'] = _resolve_file(gx_raw['ports'].get('area_file'))
        gx_raw['ports']['alphak_file'] = _resolve_file(gx_raw['ports'].get('alphak_file'))
    if isinstance(gx_raw.get('slots'), dict):
        gx_raw['slots']['alphak_file'] = _resolve_file(gx_raw['slots'].get('alphak_file'))
        for key in ('intake', 'exhaust'):
            if isinstance(gx_raw['slots'].get(key), dict):
                gx_raw['slots'][key]['alphak_file'] = _resolve_file(gx_raw['slots'][key].get('alphak_file'))
        for group_key in ('intake_groups', 'exhaust_groups'):
            groups = gx_raw['slots'].get(group_key, [])
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict):
                        group['alphak_file'] = _resolve_file(group.get('alphak_file'))

    e = raw["engine"]; g = raw["gas"]; m = raw["manifolds"]; i = raw["initial"]; s = raw["simulation"]
    it = s["integrator"]; og = s["output"]; lp = s.get("live_plot", {"enabled": False, "every_n_out": 10, "window_s": 0.02})
    gx = raw["gasexchange"]; v = gx["valves"]; p = gx["ports"]; sslots = gx.get("slots", {})
    ar = raw.get("angle_reference", {"mode": "FIRE_TDC"})
    pl = raw.get("plena", {})
    th = raw.get("throttle", {})
    em = raw.get("energy_models", {})
    pp = raw.get("postprocess", {}); se = pp.get("slot_events", {}); gc = pp.get("group_contributions", {}); gf = pp.get("group_flow_model", {})
    numerics = raw.get("numerics", {})
    links = raw.get("links", {})
    thresholds = raw.get("thresholds", {})
    plot_style = raw.get("plot_style", {})

    uc_list = raw.get("user_cylinders")
    active_name = raw.get("active_user_cylinder")
    if uc_list is None:
        uc_list = []
    if not uc_list:
        uc_list = [{
            "name": "user_cylinder_1",
            "enabled": True,
            "crank_angle_offset_deg": 0.0,
            "actuation_source": "auto",
            "notes": "",
            "connections": {"intake_name": "intake_manifold_1", "exhaust_name": "exhaust_manifold_1"},
            "runners": {
                "intake": {"enabled": True, "length_m": 0.25, "diameter_m": 0.035, "volume_m3": 0.00024, "zeta_local": 1.2, "friction_factor": 0.03, "wall_temperature_K": 320.0},
                "exhaust": {"enabled": True, "length_m": 0.35, "diameter_m": 0.030, "volume_m3": 0.00025, "zeta_local": 1.8, "friction_factor": 0.04, "wall_temperature_K": 650.0},
            },
            "piston": {"area_scale": 1.0, "crown_temperature_K": 520.0},
            "liner": {"area_scale": 1.0, "wall_temperature_K": 430.0},
            "head": {"area_scale": 1.0, "wall_temperature_K": 480.0},
        }]
    if active_name is None:
        active_name = str(uc_list[0].get("name", "user_cylinder_1"))

    return Config(
        case_name=str(raw.get("case_name", "case")),
        engine=EngineCfg(
            str(e["cycle_type"]),
            float(e["rpm"]) if "rpm" in e and e["rpm"] is not None else None,
            float(e["freq_hz"]) if "freq_hz" in e and e["freq_hz"] is not None else None,
            float(e["bore_m"]), float(e["stroke_m"]), float(e["conrod_m"]), float(e["compression_ratio"]),
        ),
        gas=GasCfg(float(g["R_J_per_kgK"]), float(g["cp_J_per_kgK"])),
        manifolds=ManifoldCfg(float(m["p_int_pa"]), float(m["T_int_K"]), float(m["p_ex_pa"]), float(m["T_ex_K"])),
        initial=InitialCfg(float(i["p0_pa"]), float(i["T0_K"])),
        simulation=SimulationCfg(
            float(s.get("t0_s", 0.0)),
            float(s.get("theta0_deg", 0.0)),
            int(s.get("n_cycles_store", s.get("n_cycles", 1))),
            int(s.get("n_cycles_compute", s.get("n_cycles_store", s.get("n_cycles", 1)))),
            IntegratorCfg(str(it.get("type", "rk4_fixed")), str(it.get("method", "RK45")), float(it.get("rtol", 1e-8)), float(it.get("atol", 1e-10)), float(it.get("max_step_s", 1e-4)), float(it.get("dt_internal_s", 1e-5))),
            OutputGridCfg(float(og["dt_out_s"]), float(og.get("dtheta_out_deg", 0.5))),
            LivePlotCfg(bool(lp.get("enabled", False)), int(lp.get("every_n_out", 10)), float(lp.get("window_s", 0.02))),
            CycleConvergenceCfg(
                enabled=bool(s.get("cycle_convergence", {}).get("enabled", False)),
                rel_tol_mass=float(s.get("cycle_convergence", {}).get("rel_tol_mass", 1e-4)),
                rel_tol_temp=float(s.get("cycle_convergence", {}).get("rel_tol_temp", 5e-4)),
                abs_tol_mass_kg=float(s.get("cycle_convergence", {}).get("abs_tol_mass_kg", 1e-8)),
                abs_tol_temp_K=float(s.get("cycle_convergence", {}).get("abs_tol_temp_K", 1e-3)),
                required_consecutive_cycles=int(s.get("cycle_convergence", {}).get("required_consecutive_cycles", 3)),
                min_cycles_before_check=int(s.get("cycle_convergence", {}).get("min_cycles_before_check", 4)),
                stop_when_converged=bool(s.get("cycle_convergence", {}).get("stop_when_converged", True)),
                verbose=bool(s.get("cycle_convergence", {}).get("verbose", True)),
                monitored_states=list(s.get("cycle_convergence", {}).get("monitored_states", [
                    "cylinder_masses",
                    "cylinder_temperatures",
                    "imep",
                    "fuel_mass_per_cycle",
                    "intake_plenum_mass",
                    "exhaust_plenum_mass",
                    "intake_plenum_temperature",
                    "exhaust_plenum_temperature",
                ])),
                rel_tol_other=float(s.get("cycle_convergence", {}).get("rel_tol_other", 5e-4)),
                abs_tol_other=float(s.get("cycle_convergence", {}).get("abs_tol_other", 1e-3)),
            ),
        ),
        gasexchange=GasExchangeCfg(
            bool(gx.get("enabled", True)),
            str(gx.get("mode", "valves")),
            str(gx.get("flow_model", "nozzle_choked")),
            ValvesCfg(str(v["lift_file"]), str(v["alphak_file"]), float(v["d_in_m"]), float(v["d_ex_m"]), int(v.get("count_in", 1)), int(v.get("count_ex", 1)), float(v["A_in_port_max_m2"]), float(v["A_ex_port_max_m2"]), dict(v["intake_open"]), dict(v["exhaust_open"]), dict(v.get("scaling", {"intake": {"angle_scale": 1.0, "lift_scale": 1.0}, "exhaust": {"angle_scale": 1.0, "lift_scale": 1.0}})), str(v.get("lift_angle_basis", "crank")), float(v.get("cam_to_crank_ratio", 2.0)), float(v.get("effective_lift_threshold_mm", 0.1))),
            PortsCfg(str(p["area_file"]), str(p["alphak_file"])),
            SlotsCfg(str(sslots.get("alphak_file", p.get("alphak_file"))), _mk_slot_geom(sslots.get("intake", {})), _mk_slot_geom(sslots.get("exhaust", {})), [_mk_slot_geom(g) for g in sslots.get("intake_groups", [])], [_mk_slot_geom(g) for g in sslots.get("exhaust_groups", [])]),
        ),
        output_files=OutputFilesCfg(str(raw["output_files"].get("out_dir", "out")), str(raw["output_files"].get("csv_name", "out.csv")), str(raw["output_files"].get("plot_name", "out.png"))),
        user_cylinders=[_mk_user_cylinder(d) for d in uc_list],
        active_user_cylinder=str(active_name),
        plena=PlenaCfg(
            enabled=bool(pl.get("enabled", True)),
            intake=PlenumSideCfg(float(pl.get("intake", {}).get("volume_m3", 0.012)), float(pl.get("intake", {}).get("p0_pa", m["p_int_pa"])), float(pl.get("intake", {}).get("T0_K", m["T_int_K"]))),
            exhaust=PlenumSideCfg(float(pl.get("exhaust", {}).get("volume_m3", 0.018)), float(pl.get("exhaust", {}).get("p0_pa", m["p_ex_pa"])), float(pl.get("exhaust", {}).get("T0_K", m["T_ex_K"]))),
        ),
        throttle=ThrottleCfg(
            enabled=bool(th.get("enabled", True)),
            diameter_m=float(th.get("diameter_m", 0.032)),
            cd=float(th.get("cd", 0.82)),
            position=float(th.get("position", 0.65)),
            position_mode=str(th.get("position_mode", "fraction")),
            A_max_m2=float(th.get("A_max_m2", 0.0)),
            T_upstream_K=float(th.get("T_upstream_K", 300.0)),
            p_upstream_pa=float(th.get("p_upstream_pa", 101325.0)),
        ),
        energy_models=dict(em),
        angle_reference=AngleReferenceCfg(
            str(ar.get("mode", "FIRE_TDC")),
            float(ar.get("plot_theta_min_deg", -360.0)),
            float(ar.get("plot_theta_max_deg", 360.0)),
        ),
        postprocess=PostprocessCfg(
            SlotEventsCfg(bool(se.get("enabled", True)), float(se.get("area_threshold_m2", 1e-7)), bool(se.get("per_group", True)), bool(se.get("per_group_blowdown", True)), bool(se.get("plot_groups", True))),
            GroupContribCfg(bool(gc.get("enabled", True)), float(gc.get("area_threshold_m2", 1e-7))),
            GroupFlowModelCfg(bool(gf.get("enabled", True)), str(gf.get("mode", "independent_nozzles_with_channel_losses"))),
        ),
        numerics=dict(numerics),
        links=dict(links),
        thresholds=dict(thresholds),
        plot_style=dict(plot_style),
    )
