import math
import numpy as np
from motor_sim.flow.nozzle_choked import mdot_nozzle_signed
from motor_sim.flow.runner_model import effective_area
from motor_sim.flow.throttle_model import throttle_area
from motor_sim.flow.port_flow import PortDefinition, signed_port_mdot, enthalpy_from_signed_flow, flow_direction_label
from motor_sim.submodels.combustion import wiebe_heat_release, combustion_angle_summary, combustion_q_total_J
from motor_sim.post.phase_logic import reference_points


class Model:
    def __init__(self, state_index, ctx):
        self.S = state_index
        self.ctx = ctx
        self.ctx.model_state = state_index
        self._combustion_cycle_cache = {}

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

    def rhs(self, t, y):
        S = self.S
        ctx = self.ctx
        ctx.reset_signals()

        theta = float(y[S.i("theta")])
        omega = ctx.engine.omega_rad_s
        dtheta_dt = omega
        dy = np.zeros_like(y)
        dy[S.i("theta")] = dtheta_dt

        gamma, R, cp, cv = ctx.gas.gamma, ctx.gas.R, ctx.gas.cp, ctx.gas.cv
        numerics = getattr(ctx.cfg, "numerics", {}) if hasattr(ctx.cfg, "numerics") else {}
        links = getattr(ctx.cfg, "links", {}) if hasattr(ctx.cfg, "links") else {}
        min_volume_m3 = float(numerics.get("min_volume_m3", 1e-12))
        min_runner_volume_m3 = float(numerics.get("min_runner_volume_m3", 1e-9))
        min_mass_kg = float(numerics.get("min_mass_kg", 1e-12))
        runner_defaults = numerics.get("runner_defaults", {})

        m_int = float(y[S.i("m_int_plenum")]); T_int = float(y[S.i("T_int_plenum")])
        m_ex = float(y[S.i("m_ex_plenum")]); T_ex = float(y[S.i("T_ex_plenum")])
        V_int = ctx.cfg.plena.intake.volume_m3; V_ex = ctx.cfg.plena.exhaust.volume_m3
        p_int = m_int * R * T_int / max(V_int, min_volume_m3)
        p_ex = m_ex * R * T_ex / max(V_ex, min_volume_m3)

        p_src_in = ctx.cfg.throttle.p_upstream_pa if ctx.cfg.throttle.enabled else ctx.cfg.manifolds.p_int_pa
        T_src_in = ctx.cfg.throttle.T_upstream_K if ctx.cfg.throttle.enabled else ctx.cfg.manifolds.T_int_K
        p_sink_ex = ctx.cfg.manifolds.p_ex_pa; T_sink_ex = ctx.cfg.manifolds.T_ex_K
        A_feed = float(links.get("plenum_feed_area_m2", 2.0e-4)); Cd_feed = float(links.get("plenum_feed_cd", 1.0))
        A_throttle = throttle_area(ctx.cfg.throttle.diameter_m, ctx.cfg.throttle.position, ctx.cfg.throttle.position_mode, ctx.cfg.throttle.A_max_m2) if ctx.cfg.throttle.enabled else A_feed
        Cd_throttle = ctx.cfg.throttle.cd if ctx.cfg.throttle.enabled else Cd_feed

        # positive: source -> plenum ; positive: exhaust plenum -> sink
        md_src_to_int = self._signed_flow_ab(p_src_in, T_src_in, p_int, T_int, Cd_throttle, A_throttle, ctx.cfg.gasexchange.flow_model, gamma, R)
        md_ex_to_sink = self._signed_flow_ab(p_ex, T_ex, p_sink_ex, T_sink_ex, Cd_feed, A_feed, ctx.cfg.gasexchange.flow_model, gamma, R)

        dm_int_total_to_runners = 0.0
        dH_int_total_to_runners = 0.0
        dm_ex_total_from_runners = 0.0
        dH_ex_total_from_runners = 0.0
        p_list = []; V_list = []; x_list = []
        runner_T_for_discharge = []

        for cyl in ctx.cylinders:
            prefix = cyl.name
            m = float(y[S.i(f"m__{prefix}")]); T = float(y[S.i(f"T__{prefix}")])
            m_rin = float(y[S.i(f"m_rin__{prefix}")]); T_rin = float(y[S.i(f"T_rin__{prefix}")])
            m_rex = float(y[S.i(f"m_rex__{prefix}")]); T_rex = float(y[S.i(f"T_rex__{prefix}")])

            rcfg = cyl.runner_cfg or {}
            rin = rcfg.get("intake", {})
            rex = rcfg.get("exhaust", {})
            V_rin = max(float(rin.get("volume_m3", runner_defaults.get("intake_volume_m3", 1e-6))), min_runner_volume_m3)
            V_rex = max(float(rex.get("volume_m3", runner_defaults.get("exhaust_volume_m3", 1e-6))), min_runner_volume_m3)
            p_rin = m_rin * R * T_rin / V_rin
            p_rex = m_rex * R * T_rex / V_rex

            geom = cyl.eval_geometry(theta)
            V = float(geom["V_m3"]); dV_dtheta = float(geom["dV_dtheta_m3_per_rad"]); x = float(geom["x_from_tdc_m"])
            theta_local_deg = float(geom.get("theta_local_deg", math.degrees(theta)))
            dV_dt = dV_dtheta * dtheta_dt
            p = ctx.gas.p_from_mTV(m, T, V)

            aux = {
                "theta": theta, "theta_deg": math.degrees(theta), "theta_local_deg": theta_local_deg,
                "omega": omega, "V": V, "dV_dt": dV_dt, "p": p, "m": m, "T": T, "x": x,
                "A_piston_m2": float(geom.get("A_piston_m2", 0.0)),
            }
            A_in_geom, Cd_in, A_ex_geom, Cd_ex, lift_in_m, lift_ex_m = cyl.eval_ports_or_valves(theta_local_deg, aux, ctx)

            if rin.get("enabled", True):
                A_in_eff, phi_in = effective_area(
                    A_in_geom,
                    rin.get("length_m", runner_defaults.get("intake_length_m", 0.25)),
                    rin.get("diameter_m", runner_defaults.get("intake_diameter_m", 0.035)),
                    rin.get("zeta_local", runner_defaults.get("intake_zeta_local", 1.2)),
                    rin.get("friction_factor", runner_defaults.get("intake_friction_factor", 0.03)),
                )
            else:
                A_in_eff, phi_in = float(A_in_geom), 1.0

            if rex.get("enabled", True):
                A_ex_eff, phi_ex = effective_area(
                    A_ex_geom,
                    rex.get("length_m", runner_defaults.get("exhaust_length_m", 0.35)),
                    rex.get("diameter_m", runner_defaults.get("exhaust_diameter_m", 0.03)),
                    rex.get("zeta_local", runner_defaults.get("exhaust_zeta_local", 1.8)),
                    rex.get("friction_factor", runner_defaults.get("exhaust_friction_factor", 0.04)),
                )
            else:
                A_ex_eff, phi_ex = float(A_ex_geom), 1.0

            A_link = float(links.get("runner_to_plenum_area_m2", 1.5e-4))

            # positive values are FROM first node TO second node
            md_int_to_rin = self._signed_flow_ab(p_int, T_int, p_rin, T_rin, 1.0, A_link, ctx.cfg.gasexchange.flow_model, gamma, R)
            md_rex_to_ex = self._signed_flow_ab(p_rex, T_rex, p_ex, T_ex, 1.0, A_link, ctx.cfg.gasexchange.flow_model, gamma, R)

            intake_port = PortDefinition(
                name=f"{prefix}_intake_port",
                direction="to_cylinder",
                area_eff_m2=A_in_eff,
                cd=Cd_in,
                area_geom_m2=A_in_geom,
                alpha_v=ctx.signals.get("valves__alphaV_in", None),
                lift_m=lift_in_m,
            )
            exhaust_port = PortDefinition(
                name=f"{prefix}_exhaust_port",
                direction="from_cylinder",
                area_eff_m2=A_ex_eff,
                cd=Cd_ex,
                area_geom_m2=A_ex_geom,
                alpha_v=ctx.signals.get("valves__alphaV_ex", None),
                lift_m=lift_ex_m,
            )

            # Signed to-cylinder convention:
            # + intake port  => flow into cylinder
            # - intake port  => intake reversion
            # - exhaust port => normal exhaust outflow
            # + exhaust port => exhaust blowback into cylinder
            md_int_to_cyl = signed_port_mdot(intake_port, p, T, p_rin, T_rin, ctx.cfg.gasexchange.flow_model, gamma, R)
            md_ex_to_cyl = signed_port_mdot(exhaust_port, p, T, p_rex, T_rex, ctx.cfg.gasexchange.flow_model, gamma, R)
            qdot_comb_W = 0.0
            xb_comb = 0.0
            dq_dtheta_deg = 0.0
            comb_cfg = getattr(ctx.cfg, "energy_models", {}).get("combustion", {}) if hasattr(ctx.cfg, "energy_models") else {}
            if bool(comb_cfg.get("enabled", False)):
                cycle_deg = float(ctx.engine.cycle_deg)
                comb_angles = combustion_angle_summary(comb_cfg, cycle_deg=cycle_deg, zot_deg=float(reference_points(cycle_deg=cycle_deg, angle_ref_mode=getattr(ctx.cfg.angle_reference, 'mode', 'FIRE_TDC'))['firing_tdc_deg']))
                soc_abs_deg = float(comb_angles["soc_abs_deg"])
                duration_deg = float(comb_angles["duration_deg"])
                wiebe_a = float(comb_angles["wiebe_a"])
                wiebe_m = float(comb_angles["wiebe_m"])

                theta_local_mod = float(theta_local_deg % cycle_deg)
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

            # Cylinder balances in signed-to-cylinder convention
            dm_dt = md_int_to_cyl + md_ex_to_cyl
            dH_int_to_cyl = enthalpy_from_signed_flow(md_int_to_cyl, cp, T, T_rin)
            dH_ex_to_cyl = enthalpy_from_signed_flow(md_ex_to_cyl, cp, T, T_rex)
            dE_dt = dH_int_to_cyl + dH_ex_to_cyl - p * dV_dt + qdot_comb_W
            dT_dt = (dE_dt / cv - T * dm_dt) / max(m, min_mass_kg)
            dy[S.i(f"m__{prefix}")] += dm_dt
            dy[S.i(f"T__{prefix}")] += dT_dt

            # Intake runner balances (positive into runner)
            dH_int_to_rin = self._enthalpy_to_b(md_int_to_rin, cp, T_int, T_rin)
            dm_rin_dt = md_int_to_rin - md_int_to_cyl
            dE_rin_dt = dH_int_to_rin - dH_int_to_cyl
            dT_rin_dt = (dE_rin_dt / cv - T_rin * dm_rin_dt) / max(m_rin, min_mass_kg)
            dy[S.i(f"m_rin__{prefix}")] += dm_rin_dt
            dy[S.i(f"T_rin__{prefix}")] += dT_rin_dt

            # Exhaust runner balances (positive into exhaust runner from cylinder is -md_ex_to_cyl)
            dH_rex_to_ex = self._enthalpy_to_b(md_rex_to_ex, cp, T_rex, T_ex)
            dm_rex_dt = -md_ex_to_cyl - md_rex_to_ex
            dE_rex_dt = -dH_ex_to_cyl - dH_rex_to_ex
            dT_rex_dt = (dE_rex_dt / cv - T_rex * dm_rex_dt) / max(m_rex, min_mass_kg)
            dy[S.i(f"m_rex__{prefix}")] += dm_rex_dt
            dy[S.i(f"T_rex__{prefix}")] += dT_rex_dt

            dm_int_total_to_runners += md_int_to_rin
            dH_int_total_to_runners += dH_int_to_rin
            dm_ex_total_from_runners += md_rex_to_ex
            dH_ex_total_from_runners += dH_rex_to_ex
            runner_T_for_discharge.append(T_rex)

            sig = {
                f"{prefix}__theta_local_deg": theta_local_deg,
                f"{prefix}__V_m3": V,
                f"{prefix}__x_m": x,
                f"{prefix}__p_cyl_pa": p,
                f"{prefix}__m_cyl_kg": m,
                f"{prefix}__T_cyl_K": T,
                f"{prefix}__mdot_intake_to_cyl_kg_s": md_int_to_cyl,
                f"{prefix}__mdot_exhaust_to_cyl_kg_s": md_ex_to_cyl,
                f"{prefix}__mdot_in_kg_s": md_int_to_cyl,
                f"{prefix}__mdot_out_kg_s": md_ex_to_cyl,
                f"{prefix}__intake_reversion_kg_s": min(md_int_to_cyl, 0.0),
                f"{prefix}__exhaust_blowback_kg_s": max(md_ex_to_cyl, 0.0),
                f"{prefix}__intake_flow_direction": flow_direction_label(md_int_to_cyl),
                f"{prefix}__exhaust_flow_direction": flow_direction_label(md_ex_to_cyl),
                f"{prefix}__A_in_m2": A_in_eff,
                f"{prefix}__A_ex_m2": A_ex_eff,
                f"{prefix}__A_in_geom_m2": A_in_geom,
                f"{prefix}__A_ex_geom_m2": A_ex_geom,
                f"{prefix}__runner_phi_in": phi_in,
                f"{prefix}__runner_phi_ex": phi_ex,
                f"{prefix}__p_rin_pa": p_rin,
                f"{prefix}__T_rin_K": T_rin,
                f"{prefix}__m_rin_kg": m_rin,
                f"{prefix}__p_rex_pa": p_rex,
                f"{prefix}__T_rex_K": T_rex,
                f"{prefix}__m_rex_kg": m_rex,
                f"{prefix}__mdot_plenum_to_rin_kg_s": md_int_to_rin,
                f"{prefix}__mdot_rin_to_cyl_kg_s": md_int_to_cyl,
                f"{prefix}__mdot_cyl_to_rex_kg_s": -md_ex_to_cyl,
                f"{prefix}__mdot_rex_to_plenum_kg_s": md_rex_to_ex,
                f"{prefix}__Cd_in": Cd_in,
                f"{prefix}__Cd_ex": Cd_ex,
                f"{prefix}__alphaV_in": ctx.signals.get("valves__alphaV_in", 0.0),
                f"{prefix}__alphaV_ex": ctx.signals.get("valves__alphaV_ex", 0.0),
                f"{prefix}__A_piston_m2": geom.get("A_piston_m2", 0.0),
                f"{prefix}__A_head_m2": geom.get("A_head_m2", 0.0),
                f"{prefix}__A_liner_wet_m2": geom.get("A_liner_wet_m2", 0.0),
                f"{prefix}__A_liner_total_m2": geom.get("A_liner_total_m2", 0.0),
                f"{prefix}__T_wall_piston_K": geom.get("T_wall_piston_K", 0.0),
                f"{prefix}__T_wall_head_K": geom.get("T_wall_head_K", 0.0),
                f"{prefix}__T_wall_liner_K": geom.get("T_wall_liner_K", 0.0),
                f"{prefix}__qdot_combustion_W": qdot_comb_W,
                f"{prefix}__xb_combustion": xb_comb,
                f"{prefix}__dq_dtheta_combustion_J_per_deg": dq_dtheta_deg,
            }
            if lift_in_m is not None:
                sig[f"{prefix}__lift_in_mm"] = 1e3 * float(lift_in_m)
            if lift_ex_m is not None:
                sig[f"{prefix}__lift_ex_mm"] = 1e3 * float(lift_ex_m)
            ctx.signals.update(sig)

            p_list.append(p); V_list.append(V); x_list.append(x)

        # Plenum balances using signed source->plenum and runner->plenum conventions
        dH_src_to_int = self._enthalpy_to_b(md_src_to_int, cp, T_src_in, T_int)
        dm_int_dt = md_src_to_int - dm_int_total_to_runners
        dE_int_dt = dH_src_to_int - dH_int_total_to_runners
        dT_int_dt = (dE_int_dt / cv - T_int * dm_int_dt) / max(m_int, min_mass_kg)

        # positive md_ex_to_sink means plenum -> sink, so plenum gets -md_ex_to_sink
        mean_T_runner_ex = float(np.mean(runner_T_for_discharge)) if runner_T_for_discharge else T_ex
        dH_ex_to_sink = self._enthalpy_to_b(md_ex_to_sink, cp, T_ex, T_sink_ex)
        dm_ex_dt = dm_ex_total_from_runners - md_ex_to_sink
        dE_ex_dt = dH_ex_total_from_runners - dH_ex_to_sink
        dT_ex_dt = (dE_ex_dt / cv - T_ex * dm_ex_dt) / max(m_ex, min_mass_kg)

        dy[S.i("m_int_plenum")] = dm_int_dt
        dy[S.i("T_int_plenum")] = dT_int_dt
        dy[S.i("m_ex_plenum")] = dm_ex_dt
        dy[S.i("T_ex_plenum")] = dT_ex_dt

        active = ctx.cylinder.name
        ctx.signals["theta_deg"] = math.degrees(theta)
        ctx.signals["theta_local_deg"] = ctx.signals.get(f"{active}__theta_local_deg", math.degrees(theta))
        ctx.signals["V"] = ctx.signals.get(f"{active}__V_m3", V_list[0] if V_list else 0.0)
        ctx.signals["x"] = ctx.signals.get(f"{active}__x_m", x_list[0] if x_list else 0.0)
        ctx.signals["p"] = ctx.signals.get(f"{active}__p_cyl_pa", p_list[0] if p_list else 0.0)
        ctx.signals["mdot_in"] = ctx.signals.get(f"{active}__mdot_intake_to_cyl_kg_s", 0.0)
        ctx.signals["mdot_out"] = ctx.signals.get(f"{active}__mdot_exhaust_to_cyl_kg_s", 0.0)
        ctx.signals["intake_reversion_kg_s"] = ctx.signals.get(f"{active}__intake_reversion_kg_s", 0.0)
        ctx.signals["exhaust_blowback_kg_s"] = ctx.signals.get(f"{active}__exhaust_blowback_kg_s", 0.0)
        ctx.signals["A_in"] = ctx.signals.get(f"{active}__A_in_m2", 0.0)
        ctx.signals["A_ex"] = ctx.signals.get(f"{active}__A_ex_m2", 0.0)
        ctx.signals["qdot_combustion_W"] = ctx.signals.get(f"{active}__qdot_combustion_W", 0.0)
        ctx.signals["xb_combustion"] = ctx.signals.get(f"{active}__xb_combustion", 0.0)
        ctx.signals["dq_dtheta_combustion_J_per_deg"] = ctx.signals.get(f"{active}__dq_dtheta_combustion_J_per_deg", 0.0)
        ctx.signals["p_cyl_mean_pa"] = float(np.mean(p_list)) if p_list else 0.0
        ctx.signals["V_total_m3"] = float(np.sum(V_list)) if V_list else 0.0
        ctx.signals["p_int_plenum_pa"] = p_int
        ctx.signals["T_int_plenum_K"] = T_int
        ctx.signals["m_int_plenum_kg"] = m_int
        ctx.signals["p_ex_plenum_pa"] = p_ex
        ctx.signals["T_ex_plenum_K"] = T_ex
        ctx.signals["m_ex_plenum_kg"] = m_ex
        ctx.signals["mdot_feed_int_kg_s"] = md_src_to_int
        ctx.signals["mdot_discharge_ex_kg_s"] = md_ex_to_sink
        ctx.signals["A_throttle_m2"] = A_throttle
        ctx.signals["Cd_throttle"] = Cd_throttle
        ctx.signals["p_upstream_throttle_pa"] = p_src_in
        ctx.signals["T_upstream_throttle_K"] = T_src_in
        return dy
