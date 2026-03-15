import math
import numpy as np

from motor_sim.core.state import StateIndex
from motor_sim.core.context import RHSContext
from motor_sim.core.model import Model

from motor_sim.kinematics.crank_slider import CrankSliderKinematics
from motor_sim.gas.idealgas import IdealGas

from motor_sim.flow.valve_profiles import ValveProfilesPeriodic
from motor_sim.flow.ports_profiles import PortsArea, AlphaK
from motor_sim.flow.slot_profiles import SlotGeom, SlotGroup, SlotBank, SlotSet
from motor_sim.flow.area_providers import ValveAreaProvider, PortsAreaProvider, SlotsAreaProvider

from motor_sim.components.user_cylinder import build_user_cylinder
'''
class Engine:
    def __init__(self, omega_rad_s: float, cycle_deg: float):
        self.omega_rad_s = float(omega_rad_s)
        self.cycle_deg = float(cycle_deg)
'''

class Engine:
    def __init__(self, omega_rad_s: float, cycle_deg: float, cfg_engine=None):

        self.omega_rad_s = float(omega_rad_s)
        self.cycle_deg = float(cycle_deg)

        # ------------------------------------------------
        # optional geometry (needed for IMEP / energy)
        # ------------------------------------------------

        if cfg_engine is not None:

            self.bore_m = float(cfg_engine.bore_m) / 1000.0
            self.stroke_m = float(cfg_engine.stroke_m) / 1000.0
            self.rod_length_m = float(cfg_engine.conrod_m) / 1000.0

            self.compression_ratio = float(cfg_engine.compression_ratio)
            self.n_cylinders = int(getattr(cfg_engine, "n_cylinders", 1))

            # piston area
            self.piston_area_m2 = math.pi / 4.0 * self.bore_m**2

            # displacement per cylinder
            self.displacement_m3 = self.piston_area_m2 * self.stroke_m

            # total displacement
            self.total_displacement_m3 = (
                self.displacement_m3 * self.n_cylinders
            )

            # clearance volume
            self.clearance_volume_m3 = (
                self.displacement_m3 / (self.compression_ratio - 1.0)
            )

        else:
            # fallback to avoid crashes
            self.displacement_m3 = 0.0
            self.total_displacement_m3 = 0.0
            self.clearance_volume_m3 = 0.0



class ModelBuilder:
    def __init__(self, cfg):
        self.cfg = cfg

    def _build_area_provider(self, cfg, cycle_deg):
        if not cfg.gasexchange.enabled:
            class DummyProvider:
                def eval(self, theta_deg, aux, ctx):
                    return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            return DummyProvider()

        if cfg.gasexchange.mode == "valves":
            prof = ValveProfilesPeriodic.from_files(
                lift_file=cfg.gasexchange.valves.lift_file,
                alphak_file=cfg.gasexchange.valves.alphak_file,
                intake_open=cfg.gasexchange.valves.intake_open,
                exhaust_open=cfg.gasexchange.valves.exhaust_open,
                scaling=cfg.gasexchange.valves.scaling,
                lift_angle_basis=cfg.gasexchange.valves.lift_angle_basis,
                cam_to_crank_ratio=cfg.gasexchange.valves.cam_to_crank_ratio,
                effective_lift_threshold_mm=cfg.gasexchange.valves.effective_lift_threshold_mm,
                cycle_deg=cycle_deg
            )
            return ValveAreaProvider(
                profiles=prof,
                d_in_m=cfg.gasexchange.valves.d_in_m,
                d_ex_m=cfg.gasexchange.valves.d_ex_m,
                count_in=cfg.gasexchange.valves.count_in,
                count_ex=cfg.gasexchange.valves.count_ex,
                A_in_max=cfg.gasexchange.valves.A_in_port_max_m2,
                A_ex_max=cfg.gasexchange.valves.A_ex_port_max_m2,
            )
        if cfg.gasexchange.mode == "ports":
            area_tbl = PortsArea.from_file(cfg.gasexchange.ports.area_file)
            ak_tbl = AlphaK.from_file(cfg.gasexchange.ports.alphak_file)
            return PortsAreaProvider(area_tbl, ak_tbl)
        if cfg.gasexchange.mode == "slots":
            def mk_geom(g):
                return SlotGeom(width_m=g.width_m, height_m=g.height_m, count=g.count, offset_from_ut_m=g.offset_from_ut_m, roof=g.roof)
            def mk_group(g):
                return SlotGroup(geom=mk_geom(g), alphak_file=g.alphak_file, channel=g.channel)
            intake_bank = SlotBank(tuple(mk_group(g) for g in cfg.gasexchange.slots.intake_groups)) if cfg.gasexchange.slots.intake_groups else SlotBank((mk_group(cfg.gasexchange.slots.intake),))
            exhaust_bank = SlotBank(tuple(mk_group(g) for g in cfg.gasexchange.slots.exhaust_groups)) if cfg.gasexchange.slots.exhaust_groups else SlotBank((mk_group(cfg.gasexchange.slots.exhaust),))
            slots = SlotSet(intake=intake_bank, exhaust=exhaust_bank)
            return SlotsAreaProvider(slots, default_alphak_file=cfg.gasexchange.slots.alphak_file)
        raise ValueError(f"Unknown gasexchange.mode: {cfg.gasexchange.mode}")

    def build(self):
        cfg = self.cfg
        if cfg.engine.rpm is not None:
            f = cfg.engine.rpm / 60.0
        elif cfg.engine.freq_hz is not None:
            f = cfg.engine.freq_hz
        else:
            raise ValueError("Provide engine.rpm or engine.freq_hz")

        omega = 2.0 * math.pi * f
        cycle_deg = 720.0 if cfg.engine.cycle_type.strip().upper() == "4T" else 360.0
        #engine = Engine(omega, cycle_deg)
        engine = Engine(omega, cycle_deg, cfg.engine)

        kin = CrankSliderKinematics(
            bore_m=cfg.engine.bore_m,
            stroke_m=cfg.engine.stroke_m,
            conrod_m=cfg.engine.conrod_m,
            compression_ratio=cfg.engine.compression_ratio
        )
        gas = IdealGas(R=cfg.gas.R_J_per_kgK, cp=cfg.gas.cp_J_per_kgK)
        area_provider = self._build_area_provider(cfg, engine.cycle_deg)

        enabled_cyls = [uc for uc in cfg.user_cylinders if uc.enabled]
        if not enabled_cyls:
            enabled_cyls = list(cfg.user_cylinders)

        cylinders = []
        for uc in enabled_cyls:
            actuation = uc.actuation_source
            if str(actuation).lower() == "auto":
                actuation = cfg.gasexchange.mode
            cylinders.append(
                build_user_cylinder(
                    name=uc.name,
                    engine=engine,
                    gas=gas,
                    kinematics=kin,
                    area_provider=area_provider,
                    connections={"intake": uc.connections.intake_name, "exhaust": uc.connections.exhaust_name, "actuation": actuation},
                    notes=uc.notes,
                    piston_cfg={"area_scale": uc.piston.area_scale, "crown_temperature_K": uc.piston.crown_temperature_K},
                    liner_cfg={"area_scale": uc.liner.area_scale, "wall_temperature_K": uc.liner.wall_temperature_K},
                    head_cfg={"area_scale": uc.head.area_scale, "wall_temperature_K": uc.head.wall_temperature_K},
                    crank_angle_offset_deg=uc.crank_angle_offset_deg,
                    runner_cfg={
                        "intake": {
                            "enabled": uc.runners.intake.enabled,
                            "length_m": uc.runners.intake.length_m,
                            "diameter_m": uc.runners.intake.diameter_m,
                            "volume_m3": uc.runners.intake.volume_m3,
                            "zeta_local": uc.runners.intake.zeta_local,
                            "friction_factor": uc.runners.intake.friction_factor,
                            "wall_temperature_K": uc.runners.intake.wall_temperature_K,
                        },
                        "exhaust": {
                            "enabled": uc.runners.exhaust.enabled,
                            "length_m": uc.runners.exhaust.length_m,
                            "diameter_m": uc.runners.exhaust.diameter_m,
                            "volume_m3": uc.runners.exhaust.volume_m3,
                            "zeta_local": uc.runners.exhaust.zeta_local,
                            "friction_factor": uc.runners.exhaust.friction_factor,
                            "wall_temperature_K": uc.runners.exhaust.wall_temperature_K,
                        },
                    },
                )
            )

        active = next((c for c in cylinders if c.name == cfg.active_user_cylinder), cylinders[0])

        names = ["theta", "m_int_plenum", "T_int_plenum", "m_ex_plenum", "T_ex_plenum"]
        for cyl in cylinders:
            names += [f"m_rin__{cyl.name}", f"T_rin__{cyl.name}", f"m_rex__{cyl.name}", f"T_rex__{cyl.name}", f"m__{cyl.name}", f"T__{cyl.name}"]
        S = StateIndex.from_names(names)

        theta0 = math.radians(cfg.simulation.theta0_deg)
        V0, _, _ = kin.volume_dVdtheta_x(theta0)
        m0 = cfg.initial.p0_pa * V0 / (gas.R * cfg.initial.T0_K)
        y0 = np.zeros(len(names), dtype=float)
        y0[S.i("theta")] = theta0
        y0[S.i("m_int_plenum")] = cfg.plena.intake.p0_pa * cfg.plena.intake.volume_m3 / (gas.R * cfg.plena.intake.T0_K)
        y0[S.i("T_int_plenum")] = cfg.plena.intake.T0_K
        y0[S.i("m_ex_plenum")] = cfg.plena.exhaust.p0_pa * cfg.plena.exhaust.volume_m3 / (gas.R * cfg.plena.exhaust.T0_K)
        y0[S.i("T_ex_plenum")] = cfg.plena.exhaust.T0_K
        runner_defaults = getattr(cfg, "numerics", {}).get("runner_defaults", {})
        min_runner_volume_m3 = float(getattr(cfg, "numerics", {}).get("min_runner_volume_m3", 1e-9))
        for cyl in cylinders:
            rcfg = cyl.runner_cfg or {}
            rin = rcfg.get("intake", {}); rex = rcfg.get("exhaust", {})
            V_rin = max(float(rin.get("volume_m3", runner_defaults.get("intake_volume_m3", 0.00024))), min_runner_volume_m3)
            T_rin = float(rin.get("wall_temperature_K", cfg.plena.intake.T0_K))
            p_rin = cfg.plena.intake.p0_pa
            y0[S.i(f"m_rin__{cyl.name}")] = p_rin * V_rin / (gas.R * T_rin)
            y0[S.i(f"T_rin__{cyl.name}")] = T_rin
            V_rex = max(float(rex.get("volume_m3", runner_defaults.get("exhaust_volume_m3", 0.00025))), min_runner_volume_m3)
            T_rex = float(rex.get("wall_temperature_K", cfg.plena.exhaust.T0_K))
            p_rex = cfg.plena.exhaust.p0_pa
            y0[S.i(f"m_rex__{cyl.name}")] = p_rex * V_rex / (gas.R * T_rex)
            y0[S.i(f"T_rex__{cyl.name}")] = T_rex
            y0[S.i(f"m__{cyl.name}")] = m0
            y0[S.i(f"T__{cyl.name}")] = cfg.initial.T0_K

        n_cycles_compute = max(int(getattr(cfg.simulation, "n_cycles_compute", cfg.simulation.n_cycles_store)), int(cfg.simulation.n_cycles_store))
        theta_end = theta0 + math.radians(engine.cycle_deg * n_cycles_compute)
        t0 = cfg.simulation.t0_s
        t_end = t0 + (theta_end - theta0) / engine.omega_rad_s

        ctx = RHSContext(cfg=cfg, engine=engine, kin=kin, gas=gas, area_provider=area_provider, submodels=[], cylinder=active, cylinders=cylinders)
        model = Model(S, ctx)
        return S, ctx, model, (t0, t_end), y0
