from dataclasses import dataclass
import math
import numpy as np
from motor_sim.flow.nozzle_choked import mdot_nozzle_signed
from motor_sim.flow.runner_model import effective_area
from motor_sim.flow.throttle_model import throttle_area
from motor_sim.flow.port_flow import PortDefinition, signed_port_mdot, enthalpy_from_signed_flow, flow_direction_label
from motor_sim.submodels.combustion import wiebe_heat_release, combustion_angle_summary, combustion_q_total_J
from motor_sim.post.phase_logic import reference_points


@dataclass(frozen=True)
class GlobalStateIdx:
    theta: int
    m_int_plenum: int
    T_int_plenum: int | None
    U_int_plenum: int | None
    m_ex_plenum: int
    T_ex_plenum: int | None
    U_ex_plenum: int | None


@dataclass(frozen=True)
class CylinderStateIdx:
    name: str
    m_cyl: int
    T_cyl: int | None
    U_cyl: int | None
    m_rin: int
    T_rin: int | None
    U_rin: int | None
    m_rex: int
    T_rex: int | None
    U_rex: int | None


@dataclass(frozen=True)
class RunnerSideCompiled:
    enabled: bool
    volume_m3: float
    length_m: float
    diameter_m: float
    zeta_local: float
    friction_factor: float


@dataclass(frozen=True)
class CylinderCompiled:
    name: str
    cyl: object
    state: CylinderStateIdx
    intake: RunnerSideCompiled
    exhaust: RunnerSideCompiled


@dataclass(frozen=True)
class RuntimeConsts:
    gamma: float
    R: float
    cp: float
    cv: float
    state_representation: str
    min_volume_m3: float
    min_runner_volume_m3: float
    min_mass_kg: float
    runner_defaults: dict
    links: dict
    p_src_in: float
    T_src_in: float
    p_sink_ex: float
    T_sink_ex: float
    A_feed: float
    Cd_feed: float
    A_runner_link: float
    flow_model: str


@dataclass
class GlobalStateSnapshot:
    theta: float
    theta_deg: float
    omega: float
    dtheta_dt: float
    m_int: float
    T_int: float
    U_int: float
    m_ex: float
    T_ex: float
    U_ex: float
    V_int: float
    V_ex: float
    p_int: float
    p_ex: float
    A_feed: float
    Cd_feed: float
    A_throttle: float
    Cd_throttle: float
    md_src_to_int: float
    md_ex_to_sink: float


@dataclass
class PlenumAccumulator:
    dm_int_total_to_runners: float = 0.0
    dH_int_total_to_runners: float = 0.0
    dm_ex_total_from_runners: float = 0.0
    dH_ex_total_from_runners: float = 0.0


@dataclass
class PrimaryTrace:
    p_list: list
    V_list: list
    x_list: list


@dataclass
class SignalAccumulator:
    cylinder_signal_items: list


@dataclass
class CylinderStateSnapshot:
    prefix: str
    cyl: object
    idx: CylinderStateIdx
    m: float
    T: float
    U: float
    m_rin: float
    T_rin: float
    U_rin: float
    m_rex: float
    T_rex: float
    U_rex: float
    V_rin: float
    V_rex: float
    p_rin: float
    p_rex: float


@dataclass
class CylinderGeometrySnapshot:
    geom: dict
    V: float
    dV_dt: float
    x: float
    p: float
    theta_local_deg: float
    aux: dict


@dataclass
class CylinderPortSnapshot:
    intake_port: PortDefinition
    exhaust_port: PortDefinition
    A_in_geom: float
    A_in_eff: float
    A_ex_geom: float
    A_ex_eff: float
    Cd_in: float
    Cd_ex: float
    phi_in: float
    phi_ex: float
    lift_in_m: float | None
    lift_ex_m: float | None
    alpha_v_in: float
    alpha_v_ex: float


@dataclass
class CylinderFlowSnapshot:
    md_int_to_rin: float
    md_rex_to_ex: float
    md_int_to_cyl: float
    md_ex_to_cyl: float
    dH_int_to_cyl: float
    dH_ex_to_cyl: float
    dH_int_to_rin: float
    dH_rex_to_ex: float


@dataclass
class CombustionState:
    qdot_comb_W: float
    xb_comb: float
    dq_dtheta_deg: float


@dataclass
class WallHeatState:
    h_piston_W_m2K: float
    h_head_W_m2K: float
    h_liner_W_m2K: float
    area_m2: float
    qdot_wall_W: float


@dataclass
class CylinderEnergyBalance:
    dm_dt: float
    dU_dt: float
    dT_dt: float
    Hdot_in_W: float
    Hdot_out_W: float
    p_dV_W: float
    qdot_wall_W: float
    qdot_comb_W: float
    residual_W: float


class Model:
    def __init__(self, state_index, ctx):
        self.S = state_index
        self.ctx = ctx
        self.ctx.model_state = state_index
        self._combustion_cycle_cache = {}
        self._compiled = self._build_compiled_runtime()

    def _cfg_section(self, name, default=None):
        cfg = getattr(self.ctx, "cfg", None)
        if cfg is None:
            return {} if default is None else default
        value = getattr(cfg, name, default)
        if value is None:
            return {} if default is None else default
        return value

    def _safe_idx(self, name):
        return self.S.idx.get(name)

    @staticmethod
    def _energy_from_mass_temp(mass, temperature, cv):
        return float(mass) * float(cv) * float(temperature)

    @staticmethod
    def _temperature_from_mass_energy(mass, energy, cv, min_mass_kg):
        return float(energy) / max(float(mass), float(min_mass_kg)) / float(cv)

    def _decode_mass_state(self, y, mass_idx, temp_idx, energy_idx, runtime):
        mass = float(y[mass_idx])
        if energy_idx is not None:
            energy = float(y[energy_idx])
            temperature = self._temperature_from_mass_energy(mass, energy, runtime.cv, runtime.min_mass_kg)
        else:
            temperature = float(y[temp_idx])
            energy = self._energy_from_mass_temp(mass, temperature, runtime.cv)
        return mass, temperature, energy

    def _apply_mass_energy_state(self, dy, runtime, mass_idx, temp_idx, energy_idx, mass, temperature, dm_dt, dU_dt):
        dy[mass_idx] += dm_dt
        if energy_idx is not None:
            dy[energy_idx] += dU_dt
        else:
            dT_dt = (dU_dt / runtime.cv - temperature * dm_dt) / max(mass, runtime.min_mass_kg)
            dy[temp_idx] += dT_dt

    def _compile_runner_side(self, side_cfg, prefix, runner_defaults, min_runner_volume_m3):
        side_cfg = side_cfg or {}
        return RunnerSideCompiled(
            enabled=bool(side_cfg.get("enabled", True)),
            volume_m3=max(float(side_cfg.get("volume_m3", runner_defaults.get(f"{prefix}_volume_m3", 1e-6))), min_runner_volume_m3),
            length_m=float(side_cfg.get("length_m", runner_defaults.get(f"{prefix}_length_m", 0.25 if prefix == "intake" else 0.35))),
            diameter_m=float(side_cfg.get("diameter_m", runner_defaults.get(f"{prefix}_diameter_m", 0.035 if prefix == "intake" else 0.03))),
            zeta_local=float(side_cfg.get("zeta_local", runner_defaults.get(f"{prefix}_zeta_local", 1.2 if prefix == "intake" else 1.8))),
            friction_factor=float(side_cfg.get("friction_factor", runner_defaults.get(f"{prefix}_friction_factor", 0.03 if prefix == "intake" else 0.04))),
        )

    def _build_compiled_runtime(self):
        numerics = self._cfg_section("numerics", {})
        links = dict(self._cfg_section("links", {}))
        runner_defaults = dict(numerics.get("runner_defaults", {}))
        min_runner_volume_m3 = float(numerics.get("min_runner_volume_m3", 1e-9))

        state_representation = str(numerics.get("state_representation", "mT"))
        idx_global = GlobalStateIdx(
            theta=self.S.i("theta"),
            m_int_plenum=self.S.i("m_int_plenum"),
            T_int_plenum=self._safe_idx("T_int_plenum"),
            U_int_plenum=self._safe_idx("U_int_plenum"),
            m_ex_plenum=self.S.i("m_ex_plenum"),
            T_ex_plenum=self._safe_idx("T_ex_plenum"),
            U_ex_plenum=self._safe_idx("U_ex_plenum"),
        )

        compiled_cylinders = []
        for cyl in self.ctx.cylinders:
            name = cyl.name
            rcfg = cyl.runner_cfg or {}
            compiled_cylinders.append(
                CylinderCompiled(
                    name=name,
                    cyl=cyl,
                    state=CylinderStateIdx(
                        name=name,
                        m_cyl=self.S.i(f"m__{name}"),
                        T_cyl=self._safe_idx(f"T__{name}"),
                        U_cyl=self._safe_idx(f"U__{name}"),
                        m_rin=self.S.i(f"m_rin__{name}"),
                        T_rin=self._safe_idx(f"T_rin__{name}"),
                        U_rin=self._safe_idx(f"U_rin__{name}"),
                        m_rex=self.S.i(f"m_rex__{name}"),
                        T_rex=self._safe_idx(f"T_rex__{name}"),
                        U_rex=self._safe_idx(f"U_rex__{name}"),
                    ),
                    intake=self._compile_runner_side(rcfg.get("intake", {}), "intake", runner_defaults, min_runner_volume_m3),
                    exhaust=self._compile_runner_side(rcfg.get("exhaust", {}), "exhaust", runner_defaults, min_runner_volume_m3),
                )
            )

        throttle_enabled = bool(getattr(self.ctx.cfg.throttle, "enabled", False))
        p_src_in = self.ctx.cfg.throttle.p_upstream_pa if throttle_enabled else self.ctx.cfg.manifolds.p_int_pa
        T_src_in = self.ctx.cfg.throttle.T_upstream_K if throttle_enabled else self.ctx.cfg.manifolds.T_int_K

        active = getattr(self.ctx, "cylinder", None)
        primary_cylinder_name = getattr(active, "name", None)
        if primary_cylinder_name is None and compiled_cylinders:
            primary_cylinder_name = compiled_cylinders[0].name

        return {
            "idx_global": idx_global,
            "cylinders": compiled_cylinders,
            "consts": RuntimeConsts(
                gamma=float(self.ctx.gas.gamma),
                R=float(self.ctx.gas.R),
                cp=float(self.ctx.gas.cp),
                cv=float(self.ctx.gas.cv),
                state_representation=state_representation,
                min_volume_m3=float(numerics.get("min_volume_m3", 1e-12)),
                min_runner_volume_m3=min_runner_volume_m3,
                min_mass_kg=float(numerics.get("min_mass_kg", 1e-12)),
                runner_defaults=runner_defaults,
                links=links,
                p_src_in=float(p_src_in),
                T_src_in=float(T_src_in),
                p_sink_ex=float(self.ctx.cfg.manifolds.p_ex_pa),
                T_sink_ex=float(self.ctx.cfg.manifolds.T_ex_K),
                A_feed=float(links.get("plenum_feed_area_m2", 2.0e-4)),
                Cd_feed=float(links.get("plenum_feed_cd", 1.0)),
                A_runner_link=float(links.get("runner_to_plenum_area_m2", 1.5e-4)),
                flow_model=str(self.ctx.cfg.gasexchange.flow_model),
            ),
            "primary_cylinder_name": primary_cylinder_name,
            "topology_preview": self._build_topology_preview(compiled_cylinders),
        }

    @staticmethod
    def _build_topology_preview(compiled_cylinders):
        nodes = ["source.intake", "plenum.intake", "plenum.exhaust", "sink.exhaust"]
        edges = [
            ("source.intake", "plenum.intake", "throttle_or_feed"),
            ("plenum.exhaust", "sink.exhaust", "discharge"),
        ]
        for cc in compiled_cylinders:
            rin = f"runner.intake.{cc.name}"
            cyl = f"cylinder.{cc.name}"
            rex = f"runner.exhaust.{cc.name}"
            nodes.extend([rin, cyl, rex])
            edges.extend([
                ("plenum.intake", rin, "runner_link_intake"),
                (rin, cyl, "intake_port"),
                (cyl, rex, "exhaust_port"),
                (rex, "plenum.exhaust", "runner_link_exhaust"),
            ])
        return {"nodes": nodes, "edges": edges}

    def _signed_flow_ab(self, p_a, T_a, p_b, T_b, Cd, A, flow_model, gamma, R):
        """Signed mass flow positive from node A -> node B."""
        A = max(float(A), 0.0)
        Cd = max(float(Cd), 0.0)
        if A <= 0.0 or Cd <= 0.0:
            return 0.0
        min_temperature_K = float(getattr(self.ctx.cfg, "numerics", {}).get("min_temperature_K", 1e-9)) if hasattr(self.ctx, "cfg") else 1e-9
        if flow_model == "nozzle_choked":
            return mdot_nozzle_signed(Cd, A, p_a, T_a, p_b, T_b, gamma, R)

        # signed orifice fallback
        if p_a >= p_b:
            sign = 1.0
            p_up, T_up, dp = p_a, T_a, p_a - p_b
        else:
            sign = -1.0
            p_up, T_up, dp = p_b, T_b, p_b - p_a
        rho = p_up / (R * max(T_up, min_temperature_K))
        mdot_mag = Cd * A * math.sqrt(max(2.0 * rho * dp, 0.0)) if rho > 0.0 and dp > 0.0 else 0.0
        return sign * mdot_mag

    @staticmethod
    def _enthalpy_to_b(mdot_ab, cp, T_a, T_b):
        """Energy term for control volume B when mdot_ab is positive A -> B."""
        if mdot_ab >= 0.0:
            return mdot_ab * cp * T_a
        return mdot_ab * cp * T_b

    def _make_rhs_output(self, y):
        compiled = self._compiled
        idx_global = compiled["idx_global"]
        omega = self.ctx.engine.omega_rad_s
        dy = np.zeros_like(y)
        dy[idx_global.theta] = omega
        return compiled, idx_global, compiled["consts"], dy

    def _read_global_state(self, y, runtime, idx_global):
        theta = float(y[idx_global.theta])
        theta_deg = math.degrees(theta)
        omega = self.ctx.engine.omega_rad_s
        dtheta_dt = omega

        m_int, T_int, U_int = self._decode_mass_state(y, idx_global.m_int_plenum, idx_global.T_int_plenum, idx_global.U_int_plenum, runtime)
        m_ex, T_ex, U_ex = self._decode_mass_state(y, idx_global.m_ex_plenum, idx_global.T_ex_plenum, idx_global.U_ex_plenum, runtime)
        V_int = self.ctx.cfg.plena.intake.volume_m3
        V_ex = self.ctx.cfg.plena.exhaust.volume_m3
        p_int = m_int * runtime.R * T_int / max(V_int, runtime.min_volume_m3)
        p_ex = m_ex * runtime.R * T_ex / max(V_ex, runtime.min_volume_m3)

        A_feed = runtime.A_feed
        Cd_feed = runtime.Cd_feed
        if self.ctx.cfg.throttle.enabled:
            A_throttle = throttle_area(
                self.ctx.cfg.throttle.diameter_m,
                self.ctx.cfg.throttle.position,
                self.ctx.cfg.throttle.position_mode,
                self.ctx.cfg.throttle.A_max_m2,
            )
            Cd_throttle = self.ctx.cfg.throttle.cd
        else:
            A_throttle = A_feed
            Cd_throttle = Cd_feed

        md_src_to_int = self._signed_flow_ab(
            runtime.p_src_in,
            runtime.T_src_in,
            p_int,
            T_int,
            Cd_throttle,
            A_throttle,
            runtime.flow_model,
            runtime.gamma,
            runtime.R,
        )
        md_ex_to_sink = self._signed_flow_ab(
            p_ex,
            T_ex,
            runtime.p_sink_ex,
            runtime.T_sink_ex,
            Cd_feed,
            A_feed,
            runtime.flow_model,
            runtime.gamma,
            runtime.R,
        )

        return GlobalStateSnapshot(
            theta=theta,
            theta_deg=theta_deg,
            omega=omega,
            dtheta_dt=dtheta_dt,
            m_int=m_int,
            T_int=T_int,
            U_int=U_int,
            m_ex=m_ex,
            T_ex=T_ex,
            U_ex=U_ex,
            V_int=V_int,
            V_ex=V_ex,
            p_int=p_int,
            p_ex=p_ex,
            A_feed=A_feed,
            Cd_feed=Cd_feed,
            A_throttle=A_throttle,
            Cd_throttle=Cd_throttle,
            md_src_to_int=md_src_to_int,
            md_ex_to_sink=md_ex_to_sink,
        )

    def _make_accumulators(self):
        return PlenumAccumulator(), PrimaryTrace(p_list=[], V_list=[], x_list=[]), SignalAccumulator(cylinder_signal_items=[])

    def _compute_combustion_state(self, prefix, theta_local_deg, m, dtheta_dt):
        ctx = self.ctx
        qdot_comb_W = 0.0
        xb_comb = 0.0
        dq_dtheta_deg = 0.0
        comb_cfg = getattr(ctx.cfg, "energy_models", {}).get("combustion", {}) if hasattr(ctx.cfg, "energy_models") else {}
        if not bool(comb_cfg.get("enabled", False)):
            return CombustionState(qdot_comb_W=0.0, xb_comb=0.0, dq_dtheta_deg=0.0)

        cycle_deg = float(ctx.engine.cycle_deg)
        comb_angles = combustion_angle_summary(
            comb_cfg,
            cycle_deg=cycle_deg,
            zot_deg=float(reference_points(cycle_deg=cycle_deg, angle_ref_mode=getattr(ctx.cfg.angle_reference, 'mode', 'FIRE_TDC'))['firing_tdc_deg']),
        )
        soc_abs_deg = float(comb_angles["soc_abs_deg"])
        duration_deg = float(comb_angles["duration_deg"])
        wiebe_a = float(comb_angles["wiebe_a"])
        wiebe_m = float(comb_angles["wiebe_m"])

        cycle_index_local = int(math.floor(float(theta_local_deg) / cycle_deg))
        cache = self._combustion_cycle_cache.setdefault(prefix, {})
        if cache.get("cycle_index") != cycle_index_local:
            cache.clear()
            cache["cycle_index"] = cycle_index_local

        q_total_cycle = cache.get("q_total_cycle_J")
        rel_deg = (float(theta_local_deg) - soc_abs_deg) % cycle_deg
        combustion_active = rel_deg <= duration_deg
        if q_total_cycle is None and combustion_active:
            q_total_cycle = combustion_q_total_J(comb_cfg, m_air_kg=max(m, 0.0))
            cache["q_total_cycle_J"] = float(q_total_cycle)
        if q_total_cycle is None:
            q_total_cycle = 0.0

        qdot_per_rad, xb_comb, dq_dtheta_deg = wiebe_heat_release(
            theta_deg=theta_local_deg,
            cycle_deg=cycle_deg,
            soc_deg=soc_abs_deg,
            duration_deg=duration_deg,
            q_total_J_per_cycle=float(q_total_cycle),
            wiebe_a=wiebe_a,
            wiebe_m=wiebe_m,
        )
        qdot_comb_W = qdot_per_rad * dtheta_dt
        return CombustionState(
            qdot_comb_W=float(qdot_comb_W),
            xb_comb=float(xb_comb),
            dq_dtheta_deg=float(dq_dtheta_deg),
        )

    def _compute_wall_heat_state(self, state, geom_state):
        cfg_energy = getattr(self.ctx.cfg, "energy_models", {}) if hasattr(self.ctx, "cfg") else {}
        wall_cfg = dict(cfg_energy.get("wall_heat", {}))
        if not bool(wall_cfg.get("enabled", False)):
            return WallHeatState(
                h_piston_W_m2K=0.0,
                h_head_W_m2K=0.0,
                h_liner_W_m2K=0.0,
                area_m2=0.0,
                qdot_wall_W=0.0,
            )

        A_p = float(geom_state.geom.get("A_piston_m2", 0.0))
        A_h = float(geom_state.geom.get("A_head_m2", 0.0))
        A_l = float(geom_state.geom.get("A_liner_wet_m2", 0.0))
        T_wp = float(geom_state.geom.get("T_wall_piston_K", state.T))
        T_wh = float(geom_state.geom.get("T_wall_head_K", state.T))
        T_wl = float(geom_state.geom.get("T_wall_liner_K", state.T))
        hp = float(wall_cfg.get("h_piston_W_m2K", 150.0))
        hh = float(wall_cfg.get("h_head_W_m2K", 180.0))
        hl = float(wall_cfg.get("h_liner_W_m2K", 130.0))

        qdot_wall_to_gas = (
            hp * A_p * (T_wp - state.T)
            + hh * A_h * (T_wh - state.T)
            + hl * A_l * (T_wl - state.T)
        )
        return WallHeatState(
            h_piston_W_m2K=hp,
            h_head_W_m2K=hh,
            h_liner_W_m2K=hl,
            area_m2=A_p + A_h + A_l,
            qdot_wall_W=float(qdot_wall_to_gas),
        )

    def _compute_cylinder_energy_balance(self, runtime, state, geom_state, flow_state, combustion_state, wall_heat_state):
        dm_dt = flow_state.md_int_to_cyl + flow_state.md_ex_to_cyl
        Hdot_in_W = max(flow_state.dH_int_to_cyl, 0.0) + max(flow_state.dH_ex_to_cyl, 0.0)
        Hdot_out_W = max(-flow_state.dH_int_to_cyl, 0.0) + max(-flow_state.dH_ex_to_cyl, 0.0)
        p_dV_W = geom_state.p * geom_state.dV_dt
        dU_dt = (
            flow_state.dH_int_to_cyl
            + flow_state.dH_ex_to_cyl
            - p_dV_W
            + wall_heat_state.qdot_wall_W
            + combustion_state.qdot_comb_W
        )
        dT_dt = (dU_dt / runtime.cv - state.T * dm_dt) / max(state.m, runtime.min_mass_kg)
        residual_W = dU_dt - (
            flow_state.dH_int_to_cyl
            + flow_state.dH_ex_to_cyl
            - p_dV_W
            + wall_heat_state.qdot_wall_W
            + combustion_state.qdot_comb_W
        )
        return CylinderEnergyBalance(
            dm_dt=float(dm_dt),
            dU_dt=float(dU_dt),
            dT_dt=float(dT_dt),
            Hdot_in_W=float(Hdot_in_W),
            Hdot_out_W=float(Hdot_out_W),
            p_dV_W=float(p_dV_W),
            qdot_wall_W=float(wall_heat_state.qdot_wall_W),
            qdot_comb_W=float(combustion_state.qdot_comb_W),
            residual_W=float(residual_W),
        )

    def _read_cylinder_state(self, y, runtime, compiled_cyl):
        idx = compiled_cyl.state
        m, T, U = self._decode_mass_state(y, idx.m_cyl, idx.T_cyl, idx.U_cyl, runtime)
        m_rin, T_rin, U_rin = self._decode_mass_state(y, idx.m_rin, idx.T_rin, idx.U_rin, runtime)
        m_rex, T_rex, U_rex = self._decode_mass_state(y, idx.m_rex, idx.T_rex, idx.U_rex, runtime)
        V_rin = compiled_cyl.intake.volume_m3
        V_rex = compiled_cyl.exhaust.volume_m3
        return CylinderStateSnapshot(
            prefix=compiled_cyl.name,
            cyl=compiled_cyl.cyl,
            idx=idx,
            m=m,
            T=T,
            U=U,
            m_rin=m_rin,
            T_rin=T_rin,
            U_rin=U_rin,
            m_rex=m_rex,
            T_rex=T_rex,
            U_rex=U_rex,
            V_rin=V_rin,
            V_rex=V_rex,
            p_rin=m_rin * runtime.R * T_rin / V_rin,
            p_rex=m_rex * runtime.R * T_rex / V_rex,
        )

    def _eval_cylinder_geometry(self, g, state):
        geom = state.cyl.eval_geometry(g.theta)
        V = float(geom["V_m3"])
        dV_dtheta = float(geom["dV_dtheta_m3_per_rad"])
        x = float(geom["x_from_tdc_m"])
        theta_local_deg = float(geom.get("theta_local_deg", g.theta_deg))
        dV_dt = dV_dtheta * g.dtheta_dt
        p = self.ctx.gas.p_from_mTV(state.m, state.T, V)
        aux = {
            "theta": g.theta,
            "theta_deg": g.theta_deg,
            "theta_local_deg": theta_local_deg,
            "omega": g.omega,
            "V": V,
            "dV_dt": dV_dt,
            "p": p,
            "m": state.m,
            "T": state.T,
            "x": x,
            "A_piston_m2": float(geom.get("A_piston_m2", 0.0)),
        }
        return CylinderGeometrySnapshot(
            geom=geom,
            V=V,
            dV_dt=dV_dt,
            x=x,
            p=p,
            theta_local_deg=theta_local_deg,
            aux=aux,
        )

    def _eval_cylinder_ports(self, state, geom_state, compiled_cyl):
        ctx = self.ctx
        A_in_geom, Cd_in, A_ex_geom, Cd_ex, lift_in_m, lift_ex_m = state.cyl.eval_ports_or_valves(
            geom_state.theta_local_deg, geom_state.aux, ctx
        )

        if compiled_cyl.intake.enabled:
            A_in_eff, phi_in = effective_area(
                A_in_geom,
                compiled_cyl.intake.length_m,
                compiled_cyl.intake.diameter_m,
                compiled_cyl.intake.zeta_local,
                compiled_cyl.intake.friction_factor,
            )
        else:
            A_in_eff, phi_in = float(A_in_geom), 1.0

        if compiled_cyl.exhaust.enabled:
            A_ex_eff, phi_ex = effective_area(
                A_ex_geom,
                compiled_cyl.exhaust.length_m,
                compiled_cyl.exhaust.diameter_m,
                compiled_cyl.exhaust.zeta_local,
                compiled_cyl.exhaust.friction_factor,
            )
        else:
            A_ex_eff, phi_ex = float(A_ex_geom), 1.0

        alpha_v_in = float(ctx.signals.get("valves__alphaV_in", 0.0))
        alpha_v_ex = float(ctx.signals.get("valves__alphaV_ex", 0.0))
        return CylinderPortSnapshot(
            intake_port=PortDefinition(
                name=f"{state.prefix}_intake_port",
                direction="to_cylinder",
                area_eff_m2=A_in_eff,
                cd=Cd_in,
                area_geom_m2=A_in_geom,
                alpha_v=ctx.signals.get("valves__alphaV_in", None),
                lift_m=lift_in_m,
            ),
            exhaust_port=PortDefinition(
                name=f"{state.prefix}_exhaust_port",
                direction="from_cylinder",
                area_eff_m2=A_ex_eff,
                cd=Cd_ex,
                area_geom_m2=A_ex_geom,
                alpha_v=ctx.signals.get("valves__alphaV_ex", None),
                lift_m=lift_ex_m,
            ),
            A_in_geom=float(A_in_geom),
            A_in_eff=float(A_in_eff),
            A_ex_geom=float(A_ex_geom),
            A_ex_eff=float(A_ex_eff),
            Cd_in=float(Cd_in),
            Cd_ex=float(Cd_ex),
            phi_in=float(phi_in),
            phi_ex=float(phi_ex),
            lift_in_m=lift_in_m,
            lift_ex_m=lift_ex_m,
            alpha_v_in=alpha_v_in,
            alpha_v_ex=alpha_v_ex,
        )

    def _compute_cylinder_flows(self, g, runtime, state, geom_state, port_state):
        A_link = runtime.A_runner_link
        md_int_to_rin = self._signed_flow_ab(
            g.p_int, g.T_int, state.p_rin, state.T_rin, 1.0, A_link, runtime.flow_model, runtime.gamma, runtime.R
        )
        md_rex_to_ex = self._signed_flow_ab(
            state.p_rex, state.T_rex, g.p_ex, g.T_ex, 1.0, A_link, runtime.flow_model, runtime.gamma, runtime.R
        )
        md_int_to_cyl = signed_port_mdot(
            port_state.intake_port, geom_state.p, state.T, state.p_rin, state.T_rin, runtime.flow_model, runtime.gamma, runtime.R
        )
        md_ex_to_cyl = signed_port_mdot(
            port_state.exhaust_port, geom_state.p, state.T, state.p_rex, state.T_rex, runtime.flow_model, runtime.gamma, runtime.R
        )
        return CylinderFlowSnapshot(
            md_int_to_rin=md_int_to_rin,
            md_rex_to_ex=md_rex_to_ex,
            md_int_to_cyl=md_int_to_cyl,
            md_ex_to_cyl=md_ex_to_cyl,
            dH_int_to_cyl=enthalpy_from_signed_flow(md_int_to_cyl, runtime.cp, state.T, state.T_rin),
            dH_ex_to_cyl=enthalpy_from_signed_flow(md_ex_to_cyl, runtime.cp, state.T, state.T_rex),
            dH_int_to_rin=self._enthalpy_to_b(md_int_to_rin, runtime.cp, g.T_int, state.T_rin),
            dH_rex_to_ex=self._enthalpy_to_b(md_rex_to_ex, runtime.cp, state.T_rex, g.T_ex),
        )

    def _apply_cylinder_balances(self, dy, runtime, state, flow_state, energy_balance, accum):
        idx = state.idx
        self._apply_mass_energy_state(dy, runtime, idx.m_cyl, idx.T_cyl, idx.U_cyl, state.m, state.T, energy_balance.dm_dt, energy_balance.dU_dt)

        dm_rin_dt = flow_state.md_int_to_rin - flow_state.md_int_to_cyl
        dU_rin_dt = flow_state.dH_int_to_rin - flow_state.dH_int_to_cyl
        self._apply_mass_energy_state(dy, runtime, idx.m_rin, idx.T_rin, idx.U_rin, state.m_rin, state.T_rin, dm_rin_dt, dU_rin_dt)

        dm_rex_dt = -flow_state.md_ex_to_cyl - flow_state.md_rex_to_ex
        dU_rex_dt = -flow_state.dH_ex_to_cyl - flow_state.dH_rex_to_ex
        self._apply_mass_energy_state(dy, runtime, idx.m_rex, idx.T_rex, idx.U_rex, state.m_rex, state.T_rex, dm_rex_dt, dU_rex_dt)

        accum.dm_int_total_to_runners += flow_state.md_int_to_rin
        accum.dH_int_total_to_runners += flow_state.dH_int_to_rin
        accum.dm_ex_total_from_runners += flow_state.md_rex_to_ex
        accum.dH_ex_total_from_runners += flow_state.dH_rex_to_ex

    def _build_cylinder_signals(self, state, geom_state, port_state, flow_state, combustion_state, wall_heat_state, energy_balance):
        prefix = state.prefix
        sig = {
            f"{prefix}__theta_local_deg": geom_state.theta_local_deg,
            f"{prefix}__V_m3": geom_state.V,
            f"{prefix}__x_m": geom_state.x,
            f"{prefix}__p_cyl_pa": geom_state.p,
            f"{prefix}__m_cyl_kg": state.m,
            f"{prefix}__T_cyl_K": state.T,
            f"{prefix}__U_cyl_J": state.U,
            f"{prefix}__mdot_intake_to_cyl_kg_s": flow_state.md_int_to_cyl,
            f"{prefix}__mdot_exhaust_to_cyl_kg_s": flow_state.md_ex_to_cyl,
            f"{prefix}__mdot_in_kg_s": flow_state.md_int_to_cyl,
            f"{prefix}__mdot_out_kg_s": flow_state.md_ex_to_cyl,
            f"{prefix}__intake_reversion_kg_s": min(flow_state.md_int_to_cyl, 0.0),
            f"{prefix}__exhaust_blowback_kg_s": max(flow_state.md_ex_to_cyl, 0.0),
            f"{prefix}__intake_flow_direction": flow_direction_label(flow_state.md_int_to_cyl),
            f"{prefix}__exhaust_flow_direction": flow_direction_label(flow_state.md_ex_to_cyl),
            f"{prefix}__A_in_m2": port_state.A_in_eff,
            f"{prefix}__A_ex_m2": port_state.A_ex_eff,
            f"{prefix}__A_in_geom_m2": port_state.A_in_geom,
            f"{prefix}__A_ex_geom_m2": port_state.A_ex_geom,
            f"{prefix}__runner_phi_in": port_state.phi_in,
            f"{prefix}__runner_phi_ex": port_state.phi_ex,
            f"{prefix}__p_rin_pa": state.p_rin,
            f"{prefix}__T_rin_K": state.T_rin,
            f"{prefix}__U_rin_J": state.U_rin,
            f"{prefix}__m_rin_kg": state.m_rin,
            f"{prefix}__p_rex_pa": state.p_rex,
            f"{prefix}__T_rex_K": state.T_rex,
            f"{prefix}__U_rex_J": state.U_rex,
            f"{prefix}__m_rex_kg": state.m_rex,
            f"{prefix}__mdot_plenum_to_rin_kg_s": flow_state.md_int_to_rin,
            f"{prefix}__mdot_rin_to_cyl_kg_s": flow_state.md_int_to_cyl,
            f"{prefix}__mdot_cyl_to_rex_kg_s": -flow_state.md_ex_to_cyl,
            f"{prefix}__mdot_rex_to_plenum_kg_s": flow_state.md_rex_to_ex,
            f"{prefix}__Cd_in": port_state.Cd_in,
            f"{prefix}__Cd_ex": port_state.Cd_ex,
            f"{prefix}__alphaV_in": port_state.alpha_v_in,
            f"{prefix}__alphaV_ex": port_state.alpha_v_ex,
            f"{prefix}__A_piston_m2": geom_state.geom.get("A_piston_m2", 0.0),
            f"{prefix}__A_head_m2": geom_state.geom.get("A_head_m2", 0.0),
            f"{prefix}__A_liner_wet_m2": geom_state.geom.get("A_liner_wet_m2", 0.0),
            f"{prefix}__A_liner_total_m2": geom_state.geom.get("A_liner_total_m2", 0.0),
            f"{prefix}__T_wall_piston_K": geom_state.geom.get("T_wall_piston_K", 0.0),
            f"{prefix}__T_wall_head_K": geom_state.geom.get("T_wall_head_K", 0.0),
            f"{prefix}__T_wall_liner_K": geom_state.geom.get("T_wall_liner_K", 0.0),
            f"{prefix}__qdot_combustion_W": combustion_state.qdot_comb_W,
            f"{prefix}__xb_combustion": combustion_state.xb_comb,
            f"{prefix}__dq_dtheta_combustion_J_per_deg": combustion_state.dq_dtheta_deg,
            f"{prefix}__qdot_wall_W": wall_heat_state.qdot_wall_W,
            f"{prefix}__heat_transfer_area_m2": wall_heat_state.area_m2,
            f"{prefix}__h_piston_W_m2K": wall_heat_state.h_piston_W_m2K,
            f"{prefix}__h_head_W_m2K": wall_heat_state.h_head_W_m2K,
            f"{prefix}__h_liner_W_m2K": wall_heat_state.h_liner_W_m2K,
            f"{prefix}__Hdot_in_W": energy_balance.Hdot_in_W,
            f"{prefix}__Hdot_out_W": energy_balance.Hdot_out_W,
            f"{prefix}__p_dV_W": energy_balance.p_dV_W,
            f"{prefix}__dU_dt_W": energy_balance.dU_dt,
            f"{prefix}__dT_dt_Kps": energy_balance.dT_dt,
            f"{prefix}__energy_balance_residual_W": energy_balance.residual_W,
        }
        if port_state.lift_in_m is not None:
            sig[f"{prefix}__lift_in_mm"] = 1e3 * float(port_state.lift_in_m)
        if port_state.lift_ex_m is not None:
            sig[f"{prefix}__lift_ex_mm"] = 1e3 * float(port_state.lift_ex_m)
        return sig

    @staticmethod
    def _update_primary_trace(trace, geom_state):
        trace.p_list.append(geom_state.p)
        trace.V_list.append(geom_state.V)
        trace.x_list.append(geom_state.x)

    def _stage_cylinder_signals(self, staged_signals, state, geom_state, port_state, flow_state, combustion_state, wall_heat_state, energy_balance):
        staged_signals.cylinder_signal_items.append(
            (state.prefix, self._build_cylinder_signals(state, geom_state, port_state, flow_state, combustion_state, wall_heat_state, energy_balance))
        )

    def _process_cylinder(self, y, dy, g, runtime, compiled_cyl, accum, trace, staged_signals):
        state = self._read_cylinder_state(y, runtime, compiled_cyl)
        geom_state = self._eval_cylinder_geometry(g, state)
        port_state = self._eval_cylinder_ports(state, geom_state, compiled_cyl)
        flow_state = self._compute_cylinder_flows(g, runtime, state, geom_state, port_state)
        combustion_state = self._compute_combustion_state(state.prefix, geom_state.theta_local_deg, state.m, g.dtheta_dt)
        wall_heat_state = self._compute_wall_heat_state(state, geom_state)
        energy_balance = self._compute_cylinder_energy_balance(runtime, state, geom_state, flow_state, combustion_state, wall_heat_state)
        self._apply_cylinder_balances(dy, runtime, state, flow_state, energy_balance, accum)
        self._stage_cylinder_signals(staged_signals, state, geom_state, port_state, flow_state, combustion_state, wall_heat_state, energy_balance)
        self._update_primary_trace(trace, geom_state)

    def _finalize_plena(self, dy, runtime, idx_global, g, accum):
        dH_src_to_int = self._enthalpy_to_b(g.md_src_to_int, runtime.cp, runtime.T_src_in, g.T_int)
        dm_int_dt = g.md_src_to_int - accum.dm_int_total_to_runners
        dU_int_dt = dH_src_to_int - accum.dH_int_total_to_runners

        dH_ex_to_sink = self._enthalpy_to_b(g.md_ex_to_sink, runtime.cp, g.T_ex, runtime.T_sink_ex)
        dm_ex_dt = accum.dm_ex_total_from_runners - g.md_ex_to_sink
        dU_ex_dt = accum.dH_ex_total_from_runners - dH_ex_to_sink

        self._apply_mass_energy_state(dy, runtime, idx_global.m_int_plenum, idx_global.T_int_plenum, idx_global.U_int_plenum, g.m_int, g.T_int, dm_int_dt, dU_int_dt)
        self._apply_mass_energy_state(dy, runtime, idx_global.m_ex_plenum, idx_global.T_ex_plenum, idx_global.U_ex_plenum, g.m_ex, g.T_ex, dm_ex_dt, dU_ex_dt)

    @staticmethod
    def _flatten_staged_signals(staged_signals):
        merged = {}
        for _prefix, item in staged_signals.cylinder_signal_items:
            merged.update(item)
        return merged

    def _publish_signals(self, compiled, g, trace, staged_signals):
        ctx = self.ctx
        cylinder_signals = self._flatten_staged_signals(staged_signals)
        ctx.signals.update(cylinder_signals)
        active = compiled["primary_cylinder_name"]
        ctx.signals["theta_deg"] = g.theta_deg
        ctx.signals["theta_local_deg"] = cylinder_signals.get(f"{active}__theta_local_deg", g.theta_deg)
        ctx.signals["V"] = cylinder_signals.get(f"{active}__V_m3", trace.V_list[0] if trace.V_list else 0.0)
        ctx.signals["x"] = cylinder_signals.get(f"{active}__x_m", trace.x_list[0] if trace.x_list else 0.0)
        ctx.signals["p"] = cylinder_signals.get(f"{active}__p_cyl_pa", trace.p_list[0] if trace.p_list else 0.0)
        ctx.signals["mdot_in"] = cylinder_signals.get(f"{active}__mdot_intake_to_cyl_kg_s", 0.0)
        ctx.signals["mdot_out"] = cylinder_signals.get(f"{active}__mdot_exhaust_to_cyl_kg_s", 0.0)
        ctx.signals["intake_reversion_kg_s"] = cylinder_signals.get(f"{active}__intake_reversion_kg_s", 0.0)
        ctx.signals["exhaust_blowback_kg_s"] = cylinder_signals.get(f"{active}__exhaust_blowback_kg_s", 0.0)
        ctx.signals["A_in"] = cylinder_signals.get(f"{active}__A_in_m2", 0.0)
        ctx.signals["A_ex"] = cylinder_signals.get(f"{active}__A_ex_m2", 0.0)
        ctx.signals["qdot_combustion_W"] = cylinder_signals.get(f"{active}__qdot_combustion_W", 0.0)
        ctx.signals["xb_combustion"] = cylinder_signals.get(f"{active}__xb_combustion", 0.0)
        ctx.signals["dq_dtheta_combustion_J_per_deg"] = cylinder_signals.get(f"{active}__dq_dtheta_combustion_J_per_deg", 0.0)
        ctx.signals["p_cyl_mean_pa"] = float(np.mean(trace.p_list)) if trace.p_list else 0.0
        ctx.signals["V_total_m3"] = float(np.sum(trace.V_list)) if trace.V_list else 0.0
        ctx.signals["p_int_plenum_pa"] = g.p_int
        ctx.signals["T_int_plenum_K"] = g.T_int
        ctx.signals["m_int_plenum_kg"] = g.m_int
        ctx.signals["U_int_plenum_J"] = g.U_int
        ctx.signals["p_ex_plenum_pa"] = g.p_ex
        ctx.signals["T_ex_plenum_K"] = g.T_ex
        ctx.signals["m_ex_plenum_kg"] = g.m_ex
        ctx.signals["U_ex_plenum_J"] = g.U_ex
        ctx.signals["mdot_feed_int_kg_s"] = g.md_src_to_int
        ctx.signals["mdot_discharge_ex_kg_s"] = g.md_ex_to_sink
        ctx.signals["A_throttle_m2"] = g.A_throttle
        ctx.signals["Cd_throttle"] = g.Cd_throttle
        ctx.signals["p_upstream_throttle_pa"] = self._compiled["consts"].p_src_in
        ctx.signals["T_upstream_throttle_K"] = self._compiled["consts"].T_src_in
        topology = compiled.get("topology_preview", {})
        ctx.signals["network_node_count"] = len(topology.get("nodes", []))
        ctx.signals["network_edge_count"] = len(topology.get("edges", []))
        ctx.signals["state_representation"] = self._compiled["consts"].state_representation

    def rhs(self, t, y):
        ctx = self.ctx
        ctx.reset_signals()

        compiled, idx_global, runtime, dy = self._make_rhs_output(y)
        g = self._read_global_state(y, runtime, idx_global)
        accum, trace, staged_signals = self._make_accumulators()

        for compiled_cyl in compiled["cylinders"]:
            self._process_cylinder(y, dy, g, runtime, compiled_cyl, accum, trace, staged_signals)

        self._finalize_plena(dy, runtime, idx_global, g, accum)
        self._publish_signals(compiled, g, trace, staged_signals)
        return dy
