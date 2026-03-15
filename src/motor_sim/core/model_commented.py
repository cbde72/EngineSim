import math
import numpy as np

# Düsen-/Drosselmodell für kompressible, ggf. gechokte Strömung.
# Erwartet typischerweise Cd, A, p_up, T_up, p_dn, gamma, R und liefert
# einen positiven Massenstrombetrag in der lokalen Richtung up -> down.
from motor_sim.flow.nozzle_choked import mdot_nozzle

# Vereinfachtes Orifice-Modell als Fallback.
# Arbeitet mit Dichte rho und Druckdifferenz dp und liefert ebenfalls
# einen positiven Massenstrombetrag in der vorgegebenen Richtung.
from motor_sim.flow.simple_orifice import mdot_orifice

# Reduziert eine geometrische Öffnungsfläche auf eine effektive hydraulische
# Fläche unter Berücksichtigung von Länge, Durchmesser, lokalen Verlusten
# und Reibung im Runner.
from motor_sim.flow.runner_model import effective_area

# Berechnet die wirksame Drosselfläche aus Drosselgeometrie und Stellung.
from motor_sim.flow.throttle_model import throttle_area

# Optionales Verbrennungs-Teilmodell für die Wärmefreisetzung über eine
# Wiebe-Funktion. Liefert u. a. Wärmefreisetzung pro Kurbelwinkel und
# den umgesetzten Verbrennungsfortschritt xb.
from motor_sim.submodels.combustion import wiebe_heat_release, combustion_angle_summary, combustion_q_total_J
from motor_sim.post.phase_logic import reference_points


class Model:
    """
    Zentrales ODE-Modell der MotorSim-Referenzbasis.

    Diese Klasse formuliert die rechte Seite des Differentialgleichungssystems

        dy/dt = f(t, y)

    für den numerischen Integrator.

    In der hier vorliegenden Referenzdatei werden gekoppelt:
    - globaler Winkelzustand theta
    - Ansaugplenum
    - Abgasplenum
    - pro Zylinder:
        * Zylinderkontrollvolumen
        * Ansaugrunner
        * Abgasrunner
    - Port-/Ventilströmung
    - optional ein Wiebe-basiertes Verbrennungsmodell
    - umfangreiche Diagnose-/Plot-Signale

    Modellcharakter
    ---------------
    Das Modell ist ein konzentriertes Mehrvolumenmodell. Jeder Zylinder,
    jeder Runner und jedes Plenum wird als homogenes Kontrollvolumen
    behandelt.

    Wichtige Grundgleichungen
    -------------------------
    Druckgleichung für ideale Gase:
        p = m * R * T / V

    Zylinder-Massenbilanz:
        dm/dt = mdot_in - mdot_out

    Zylinder-Energiebilanz in der Referenzdatei:
        dE/dt = mdot_in * cp * T_in
              - mdot_out * cp * T
              - p * dV/dt
              + qdot_comb

    Temperaturgleichung aus E = m * cv * T:
        dT/dt = (dE/dt / cv - T * dm/dt) / m

    Hinweis zur Vorzeichenkonvention
    --------------------------------
    Die aktuelle Referenzdatei arbeitet lokal mit positiv gerichteten
    Flussgrößen entlang der Kette:

        Plenum -> Intake Runner -> Cylinder -> Exhaust Runner -> Plenum

    Sie ist also noch nicht vollständig auf die gewünschte globale
    signed-Konvention
        "in den Zylinder positiv, aus dem Zylinder negativ"
    umgestellt.

    Rolle im Projekt
    ----------------
    Diese Klasse ist der physikalische Kern der transienten Simulation.
    Sie ruft externe Teilmodelle für Strömung, Drossel, Runnerverluste und
    Verbrennung auf und schreibt parallel viele Diagnosegrößen in
    ctx.signals für GUI, Logger und Plotter.
    """

    def __init__(self, state_index, ctx):
        """
        Initialisiert das Modell mit Zustandsindex und globalem Kontext.

        Parameters
        ----------
        state_index :
            Mapping / Zugriffshilfe für den Zustandsvektor y.
            Beispiel:
                S.i("theta") -> Index des Winkelzustands
                S.i("m__cyl1") -> Index der Zylindermasse
        ctx :
            Globaler Simulationskontext. Enthält u. a.
            - engine
            - gas
            - cfg
            - cylinders
            - signals
            - Hilfsmethoden wie reset_signals()

        Bemerkung
        ---------
        Das state_index-Mapping wird zusätzlich unter ctx.model_state
        abgelegt, damit andere Projektteile dieselbe Zustandsdefinition
        verwenden können.
        """
        # Alias auf die Zustandsindex-Verwaltung.
        self.S = state_index

        # Globaler Simulationskontext mit Zugriff auf alle Teilmodelle,
        # Konfigurationen und Diagnosepuffer.
        self.ctx = ctx

        # Spiegelung des Zustandsindex in den Kontext.
        # Praktisch für Logger, GUI oder Hilfsroutinen.
        self.ctx.model_state = state_index
        self._combustion_cycle_cache = {}

    def _flow(self, p_up, T_up, p_dn, T_dn, Cd, A, flow_model, gamma, R):
        """
        Berechnet einen Massenstrom durch ein generisches Strömungselement.

        Parameters
        ----------
        p_up, T_up :
            Upstream-Druck und -Temperatur
        p_dn, T_dn :
            Downstream-Druck und -Temperatur
            (T_dn wird im aktuellen Fallback nicht direkt benutzt, bleibt
            aber in der Signatur für einheitliche Schnittstellen erhalten)
        Cd :
            Ausflussbeiwert / discharge coefficient
        A :
            Wirksame Strömungsfläche
        flow_model :
            Name des zu verwendenden Strömungsmodells
        gamma, R :
            Isentropenexponent und spezifische Gaskonstante

        Returns
        -------
        float
            Positiver Massenstrombetrag in Aufrufrichtung up -> down.

        Implementierte Logik
        --------------------
        1. Bei flow_model == "nozzle_choked":
           Verwendung des kompressiblen Düsenmodells.

        2. Sonst:
           Fallback auf ein einfaches Orifice-Modell mit
           rho = p_up / (R * T_up)
           dp  = max(p_up - p_dn, 0)

        Wichtige fachliche Beobachtung
        ------------------------------
        Im Orifice-Fallback wird negative Druckdifferenz abgeschnitten.
        Damit ist dort keine Rückströmung abgebildet.
        """
        # Bevorzugtes physikalisches Modell: kompressible Düse / Choked-Flow.
        if flow_model == "nozzle_choked":
            return mdot_nozzle(Cd, A, p_up, T_up, p_dn, gamma, R)

        # Numerische Schutztemperatur aus der Konfiguration.
        # Fallback auf sehr kleinen positiven Wert, um Division durch Null
        # in rho = p / (R*T) zu vermeiden.
        min_temperature_K = (
            float(getattr(self.ctx.cfg, "numerics", {}).get("min_temperature_K", 1e-9))
            if hasattr(self.ctx, "cfg")
            else 1e-9
        )

        # Dichte aus dem Upstream-Zustand.
        rho = p_up / (R * max(T_up, min_temperature_K))

        # Im einfachen Orifice-Fallback wird nur Strömung bei p_up > p_dn
        # zugelassen. Negative Druckdifferenz wird auf Null gekappt.
        dp = max(p_up - p_dn, 0.0)

        # Positiver Massenstrombetrag in lokaler Aufrufrichtung up -> down.
        return mdot_orifice(Cd, A, rho, dp)

    def rhs(self, t, y):
        """
        Berechnet die rechte Seite des ODE-Systems.

        Parameters
        ----------
        t :
            Aktuelle Integrationszeit [s]
            Wird in der aktuellen Referenzdatei nicht explizit verwendet,
            gehört aber zur standardmäßigen ODE-Solver-Signatur.
        y :
            Zustandsvektor der Simulation

        Returns
        -------
        numpy.ndarray
            Ableitungsvektor dy/dt mit derselben Struktur wie y

        Inhaltlich gelöstes System
        --------------------------
        Global:
            dtheta/dt = omega

        Für jeden Zylinder:
            p = p(m, T, V)
            dm/dt aus Gaswechsel
            dT/dt aus Energiebilanz und Massenbilanz

        Für Intake/Exhaust-Runner:
            jeweilige Massen- und Energiebilanzen

        Für Ansaug- und Abgasplenum:
            jeweilige Massen- und Energiebilanzen

        Zusätzlich:
            Aufbau eines umfangreichen Signalpakets für Plotting/Debugging.
        """
        # Kürzere Alias-Namen für bessere Lesbarkeit.
        S = self.S
        ctx = self.ctx

        # Diagnose-/Plot-Signale zu Beginn des Solver-Schrittes zurücksetzen.
        ctx.reset_signals()

        # ------------------------------------------------------------------
        # 1) Globaler Winkelzustand
        # ------------------------------------------------------------------

        # Aktuellen Kurbelwinkel aus dem Zustandsvektor lesen.
        theta = float(y[S.i("theta")])

        # Motordrehzahl als Winkelgeschwindigkeit [rad/s].
        omega = ctx.engine.omega_rad_s

        # Winkelableitung:
        #   dtheta/dt = omega
        dtheta_dt = omega

        # Ableitungsvektor mit gleicher Form wie y anlegen.
        dy = np.zeros_like(y)

        # Winkelableitung eintragen.
        dy[S.i("theta")] = dtheta_dt

        # ------------------------------------------------------------------
        # 2) Gasdaten und numerische Schutzwerte
        # ------------------------------------------------------------------

        # Idealgas-/Stoffwerte.
        gamma, R, cp, cv = ctx.gas.gamma, ctx.gas.R, ctx.gas.cp, ctx.gas.cv

        # Konfigurationsblöcke laden; wenn nicht vorhanden, auf leere Dicts
        # zurückfallen.
        numerics = getattr(ctx.cfg, "numerics", {}) if hasattr(ctx.cfg, "numerics") else {}
        links = getattr(ctx.cfg, "links", {}) if hasattr(ctx.cfg, "links") else {}

        # Numerische Untergrenzen gegen Singularitäten.
        min_temperature_K = float(numerics.get("min_temperature_K", 1e-9))
        min_volume_m3 = float(numerics.get("min_volume_m3", 1e-12))
        min_runner_volume_m3 = float(numerics.get("min_runner_volume_m3", 1e-9))
        min_mass_kg = float(numerics.get("min_mass_kg", 1e-12))

        # Defaultwerte für Intake-/Exhaust-Runner, falls pro Zylinder
        # keine vollständige Runner-Konfiguration angegeben ist.
        runner_defaults = numerics.get("runner_defaults", {})

        # ------------------------------------------------------------------
        # 3) Dynamische Plenazustände
        # ------------------------------------------------------------------

        # Zustände des Ansaugplenums lesen.
        m_int = float(y[S.i("m_int_plenum")])
        T_int = float(y[S.i("T_int_plenum")])

        # Zustände des Abgasplenums lesen.
        m_ex = float(y[S.i("m_ex_plenum")])
        T_ex = float(y[S.i("T_ex_plenum")])

        # Feste geometrische Plenumvolumina aus der Konfiguration.
        V_int = ctx.cfg.plena.intake.volume_m3
        V_ex = ctx.cfg.plena.exhaust.volume_m3

        # Drucke der Plena aus der idealen Gasgleichung.
        p_int = m_int * R * T_int / max(V_int, min_volume_m3)
        p_ex = m_ex * R * T_ex / max(V_ex, min_volume_m3)

        # ------------------------------------------------------------------
        # 4) Äußere Randbedingungen / Drossel / Feed
        # ------------------------------------------------------------------

        # Einlass-Upstream-Zustand:
        # Wenn Drossel aktiv ist, kommen die Upstream-Werte aus cfg.throttle,
        # sonst direkt aus den vorgegebenen Manifold-Randbedingungen.
        p_src_in = (
            ctx.cfg.throttle.p_upstream_pa
            if ctx.cfg.throttle.enabled
            else ctx.cfg.manifolds.p_int_pa
        )
        T_src_in = (
            ctx.cfg.throttle.T_upstream_K
            if ctx.cfg.throttle.enabled
            else ctx.cfg.manifolds.T_int_K
        )

        # Abgasseitige äußere Senke.
        p_sink_ex = ctx.cfg.manifolds.p_ex_pa
        T_sink_ex = ctx.cfg.manifolds.T_ex_K

        # Geometrie-/Beiwertparameter für die Kopplung der Plena nach außen.
        A_feed = float(links.get("plenum_feed_area_m2", 2.0e-4))
        Cd_feed = float(links.get("plenum_feed_cd", 1.0))

        # Wenn Drossel aktiv ist, wird ihre aktuelle wirksame Fläche verwendet.
        # Sonst wird einfach die Feed-Fläche benutzt.
        A_throttle = (
            throttle_area(
                ctx.cfg.throttle.diameter_m,
                ctx.cfg.throttle.position,
                ctx.cfg.throttle.position_mode,
                ctx.cfg.throttle.A_max_m2,
            )
            if ctx.cfg.throttle.enabled
            else A_feed
        )

        # Ausflussbeiwert der Drossel bzw. Feed-Verbindung.
        Cd_throttle = ctx.cfg.throttle.cd if ctx.cfg.throttle.enabled else Cd_feed

        # Massenstrom von der äußeren Einlassquelle in das Ansaugplenum.
        md_in_feed = self._flow(
            p_src_in,
            T_src_in,
            p_int,
            T_int,
            Cd_throttle,
            A_throttle,
            ctx.cfg.gasexchange.flow_model,
            gamma,
            R,
        )

        # Massenstrom vom Abgasplenum in die äußere Abgassenke.
        md_ex_discharge = self._flow(
            p_ex,
            T_ex,
            p_sink_ex,
            T_sink_ex,
            Cd_feed,
            A_feed,
            ctx.cfg.gasexchange.flow_model,
            gamma,
            R,
        )

        # ------------------------------------------------------------------
        # 5) Sammelgrößen über alle Zylinder
        # ------------------------------------------------------------------

        # Summe der Massenströme vom Ansaugplenum in alle Intake-Runner.
        dm_int_total_to_runners = 0.0

        # Summe der Massenströme aus allen Exhaust-Runnern ins Abgasplenum.
        dm_ex_total_from_runners = 0.0

        # Sammellisten für Diagnosegrößen.
        p_list = []
        V_list = []
        x_list = []

        # Für die Abgasplenum-Energiebilanz wird später eine mittlere
        # Runner-Abgastemperatur verwendet.
        runner_T_for_discharge = []

        # ------------------------------------------------------------------
        # 6) Hauptschleife über alle Zylinder
        # ------------------------------------------------------------------
        for cyl in ctx.cylinders:
            # Zylinderpräfix für die Zustandsnamen, z. B. "cyl_1".
            prefix = cyl.name

            # --------------------------------------------------------------
            # 6.1) Zylinderzustände lesen
            # --------------------------------------------------------------

            # Zylindermasse und -temperatur.
            m = float(y[S.i(f"m__{prefix}")])
            T = float(y[S.i(f"T__{prefix}")])

            # --------------------------------------------------------------
            # 6.2) Runnerzustände lesen
            # --------------------------------------------------------------

            # Intake-Runner: Masse und Temperatur.
            m_rin = float(y[S.i(f"m_rin__{prefix}")])
            T_rin = float(y[S.i(f"T_rin__{prefix}")])

            # Exhaust-Runner: Masse und Temperatur.
            m_rex = float(y[S.i(f"m_rex__{prefix}")])
            T_rex = float(y[S.i(f"T_rex__{prefix}")])

            # Zylinderspezifische Runner-Konfiguration.
            rcfg = cyl.runner_cfg or {}
            rin = rcfg.get("intake", {})
            rex = rcfg.get("exhaust", {})

            # Runner-Volumina; falls nicht gesetzt, werden Defaultwerte benutzt.
            # Gleichzeitig Schutz gegen zu kleine Volumina.
            V_rin = max(
                float(rin.get("volume_m3", runner_defaults.get("intake_volume_m3", 1e-6))),
                min_runner_volume_m3,
            )
            V_rex = max(
                float(rex.get("volume_m3", runner_defaults.get("exhaust_volume_m3", 1e-6))),
                min_runner_volume_m3,
            )

            # Runnerdrucke aus idealer Gasgleichung.
            p_rin = m_rin * R * T_rin / V_rin
            p_rex = m_rex * R * T_rex / V_rex

            # --------------------------------------------------------------
            # 6.3) Zylindergeometrie aus aktuellem Winkel
            # --------------------------------------------------------------

            # Geometrie-/Kinematikdaten des Zylinders zum aktuellen Winkel.
            geom = cyl.eval_geometry(theta)

            # Zylindervolumen V, Ableitung dV/dtheta und Kolbenweg x.
            V = float(geom["V_m3"])
            dV_dtheta = float(geom["dV_dtheta_m3_per_rad"])
            x = float(geom["x_from_tdc_m"])

            # Lokaler Zylinderwinkel in Grad, falls vom Geometriemodell
            # explizit bereitgestellt; sonst Umrechnung aus globalem theta.
            theta_local_deg = float(geom.get("theta_local_deg", math.degrees(theta)))

            # Zeitliche Volumenänderung:
            #   dV/dt = (dV/dtheta) * (dtheta/dt)
            dV_dt = dV_dtheta * dtheta_dt

            # Zylinderdruck aus dem Gasmodell.
            p = ctx.gas.p_from_mTV(m, T, V)

            # --------------------------------------------------------------
            # 6.4) Hilfsdaten für Port-/Ventilmodell
            # --------------------------------------------------------------

            # Zusatzdaten, die an Port-/Ventilmodelle übergeben werden können.
            aux = {
                "theta": theta,
                "theta_deg": math.degrees(theta),
                "theta_local_deg": theta_local_deg,
                "omega": omega,
                "V": V,
                "dV_dt": dV_dt,
                "p": p,
                "m": m,
                "T": T,
                "x": x,
                "A_piston_m2": float(geom.get("A_piston_m2", 0.0)),
            }

            # Aus der Steuerzeiten-/Ventilgeometrie:
            # - geometrische Einlassfläche
            # - Einlass-Cd
            # - geometrische Auslassfläche
            # - Auslass-Cd
            # - optionale Hübe
            (
                A_in_geom,
                Cd_in,
                A_ex_geom,
                Cd_ex,
                lift_in_m,
                lift_ex_m,
            ) = cyl.eval_ports_or_valves(theta_local_deg, aux, ctx)

            # --------------------------------------------------------------
            # 6.5) Hydraulische Reduktion der Runnerflächen
            # --------------------------------------------------------------

            # Intake-Seite:
            # Wenn Runnermodell aktiv ist, wird die geometrische Portfläche
            # auf eine wirksame hydraulische Fläche reduziert.
            if rin.get("enabled", True):
                A_in_eff, phi_in = effective_area(
                    A_in_geom,
                    rin.get("length_m", runner_defaults.get("intake_length_m", 0.25)),
                    rin.get("diameter_m", runner_defaults.get("intake_diameter_m", 0.035)),
                    rin.get("zeta_local", runner_defaults.get("intake_zeta_local", 1.2)),
                    rin.get("friction_factor", runner_defaults.get("intake_friction_factor", 0.03)),
                )
            else:
                # Ohne Runnerkorrektur bleibt die wirksame Fläche gleich
                # der geometrischen Fläche; phi = 1 bedeutet keine Reduktion.
                A_in_eff, phi_in = float(A_in_geom), 1.0

            # Exhaust-Seite analog.
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

            # --------------------------------------------------------------
            # 6.6) Teilströme im Gaswechselpfad
            # --------------------------------------------------------------

            # Koppelquerschnitt zwischen Runner und Plenum.
            A_link = float(links.get("runner_to_plenum_area_m2", 1.5e-4))

            # 1) Ansaugplenum -> Intake-Runner
            md_plenum_to_rin = self._flow(
                p_int,
                T_int,
                p_rin,
                T_rin,
                1.0,
                A_link,
                ctx.cfg.gasexchange.flow_model,
                gamma,
                R,
            )

            # 2) Intake-Runner -> Zylinder
            md_rin_to_cyl = self._flow(
                p_rin,
                T_rin,
                p,
                T,
                Cd_in,
                A_in_eff,
                ctx.cfg.gasexchange.flow_model,
                gamma,
                R,
            )

            # 3) Zylinder -> Exhaust-Runner
            md_cyl_to_rex = self._flow(
                p,
                T,
                p_rex,
                T_rex,
                Cd_ex,
                A_ex_eff,
                ctx.cfg.gasexchange.flow_model,
                gamma,
                R,
            )

            # 4) Exhaust-Runner -> Abgasplenum
            md_rex_to_plenum = self._flow(
                p_rex,
                T_rex,
                p_ex,
                T_ex,
                1.0,
                A_link,
                ctx.cfg.gasexchange.flow_model,
                gamma,
                R,
            )

            # --------------------------------------------------------------
            # 6.7) Optionale Wärmefreisetzung durch Verbrennung
            # --------------------------------------------------------------

            # Standardmäßig keine Verbrennung.
            qdot_comb_W = 0.0
            xb_comb = 0.0
            dq_dtheta_deg = 0.0

            # Verbrennungs-Konfiguration laden.
            comb_cfg = (
                getattr(ctx.cfg, "energy_models", {}).get("combustion", {})
                if hasattr(ctx.cfg, "energy_models")
                else {}
            )

            # Falls aktiviert, Wiebe-basierte Wärmefreisetzung berechnen.
            if bool(comb_cfg.get("enabled", False)):
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

                # Umrechnung von Wärmefreisetzung pro rad auf Leistung [W].
                qdot_comb_W = qdot_per_rad * dtheta_dt

            # --------------------------------------------------------------
            # 6.8) Zylinderbilanzen
            # --------------------------------------------------------------

            # Zylinder-Massenbilanz:
            # Einlass erhöht, Auslass reduziert die Zylindermasse.
            dm_dt = md_rin_to_cyl - md_cyl_to_rex

            # Zylinder-Energiebilanz:
            # + Enthalpiestrom vom Intake-Runner
            # - Enthalpiestrom zum Exhaust-Runner
            # - Volumenarbeit p*dV/dt
            # + Verbrennungswärmefreisetzung
            dE_dt = (
                md_rin_to_cyl * cp * T_rin
                - md_cyl_to_rex * cp * T
                - p * dV_dt
                + qdot_comb_W
            )

            # Temperaturableitung aus E = m * cv * T.
            dT_dt = (dE_dt / cv - T * dm_dt) / max(m, min_mass_kg)

            # In den globalen Ableitungsvektor schreiben.
            dy[S.i(f"m__{prefix}")] += dm_dt
            dy[S.i(f"T__{prefix}")] += dT_dt

            # --------------------------------------------------------------
            # 6.9) Intake-Runner-Bilanzen
            # --------------------------------------------------------------

            # Massenbilanz des Intake-Runners.
            dm_rin_dt = md_plenum_to_rin - md_rin_to_cyl

            # Energiebilanz des Intake-Runners.
            dE_rin_dt = md_plenum_to_rin * cp * T_int - md_rin_to_cyl * cp * T_rin

            # Temperaturgleichung des Intake-Runners.
            dT_rin_dt = (dE_rin_dt / cv - T_rin * dm_rin_dt) / max(m_rin, min_mass_kg)

            # In Ableitungsvektor schreiben.
            dy[S.i(f"m_rin__{prefix}")] += dm_rin_dt
            dy[S.i(f"T_rin__{prefix}")] += dT_rin_dt

            # --------------------------------------------------------------
            # 6.10) Exhaust-Runner-Bilanzen
            # --------------------------------------------------------------

            # Massenbilanz des Exhaust-Runners.
            dm_rex_dt = md_cyl_to_rex - md_rex_to_plenum

            # Energiebilanz des Exhaust-Runners.
            dE_rex_dt = md_cyl_to_rex * cp * T - md_rex_to_plenum * cp * T_rex

            # Temperaturgleichung des Exhaust-Runners.
            dT_rex_dt = (dE_rex_dt / cv - T_rex * dm_rex_dt) / max(m_rex, min_mass_kg)

            # In Ableitungsvektor schreiben.
            dy[S.i(f"m_rex__{prefix}")] += dm_rex_dt
            dy[S.i(f"T_rex__{prefix}")] += dT_rex_dt

            # --------------------------------------------------------------
            # 6.11) Beiträge für spätere Plenumbilanzen sammeln
            # --------------------------------------------------------------

            dm_int_total_to_runners += md_plenum_to_rin
            dm_ex_total_from_runners += md_rex_to_plenum
            runner_T_for_discharge.append(T_rex)

            # --------------------------------------------------------------
            # 6.12) Diagnose-/Signalsammlung pro Zylinder
            # --------------------------------------------------------------

            sig = {
                f"{prefix}__theta_local_deg": theta_local_deg,
                f"{prefix}__V_m3": V,
                f"{prefix}__x_m": x,
                f"{prefix}__p_cyl_pa": p,
                f"{prefix}__m_cyl_kg": m,
                f"{prefix}__T_cyl_K": T,
                f"{prefix}__mdot_in_kg_s": md_rin_to_cyl,
                f"{prefix}__mdot_out_kg_s": md_cyl_to_rex,
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
                f"{prefix}__mdot_plenum_to_rin_kg_s": md_plenum_to_rin,
                f"{prefix}__mdot_rin_to_cyl_kg_s": md_rin_to_cyl,
                f"{prefix}__mdot_cyl_to_rex_kg_s": md_cyl_to_rex,
                f"{prefix}__mdot_rex_to_plenum_kg_s": md_rex_to_plenum,
                f"{prefix}__Cd_in": Cd_in,
                f"{prefix}__Cd_ex": Cd_ex,
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

            # Ventilhübe nur loggen, wenn sie tatsächlich vom
            # Ventil-/Portmodell geliefert wurden.
            if lift_in_m is not None:
                sig[f"{prefix}__lift_in_mm"] = 1e3 * float(lift_in_m)
            if lift_ex_m is not None:
                sig[f"{prefix}__lift_ex_mm"] = 1e3 * float(lift_ex_m)

            # Signale in den globalen Diagnosespeicher schreiben.
            ctx.signals.update(sig)

            # Sammelgrößen für globale Auswertung.
            p_list.append(p)
            V_list.append(V)
            x_list.append(x)

        # ------------------------------------------------------------------
        # 7) Plenumbilanzen
        # ------------------------------------------------------------------

        # Ansaugplenum:
        # Zufuhr von außen minus Abfluss zu allen Intake-Runnern.
        dm_int_dt = md_in_feed - dm_int_total_to_runners
        dE_int_dt = md_in_feed * cp * T_src_in - dm_int_total_to_runners * cp * T_int
        dT_int_dt = (dE_int_dt / cv - T_int * dm_int_dt) / max(m_int, min_mass_kg)

        # Mittlere Abgastemperatur aller Exhaust-Runner als einfacher
        # Mischungsansatz für den Energieeintrag ins Abgasplenum.
        mean_T_runner_ex = float(np.mean(runner_T_for_discharge)) if runner_T_for_discharge else T_ex

        # Abgasplenum:
        # Zufluss aus allen Exhaust-Runnern minus Abfluss nach außen.
        dm_ex_dt = dm_ex_total_from_runners - md_ex_discharge
        dE_ex_dt = dm_ex_total_from_runners * cp * mean_T_runner_ex - md_ex_discharge * cp * T_ex
        dT_ex_dt = (dE_ex_dt / cv - T_ex * dm_ex_dt) / max(m_ex, min_mass_kg)

        # Ableitungen der Plenumzustände schreiben.
        dy[S.i("m_int_plenum")] = dm_int_dt
        dy[S.i("T_int_plenum")] = dT_int_dt
        dy[S.i("m_ex_plenum")] = dm_ex_dt
        dy[S.i("T_ex_plenum")] = dT_ex_dt

        # ------------------------------------------------------------------
        # 8) Globale Kurzsignale für aktiven Zylinder / GUI / Plotter
        # ------------------------------------------------------------------

        # Aktiver Zylinder, dessen Werte zusätzlich unter generischen Namen
        # abgelegt werden.
        active = ctx.cylinder.name

        # Generische Kurzwörter für Plotter und GUI.
        ctx.signals["theta_deg"] = math.degrees(theta)
        ctx.signals["theta_local_deg"] = ctx.signals.get(
            f"{active}__theta_local_deg",
            math.degrees(theta),
        )
        ctx.signals["V"] = ctx.signals.get(f"{active}__V_m3", V_list[0] if V_list else 0.0)
        ctx.signals["x"] = ctx.signals.get(f"{active}__x_m", x_list[0] if x_list else 0.0)
        ctx.signals["p"] = ctx.signals.get(f"{active}__p_cyl_pa", p_list[0] if p_list else 0.0)
        ctx.signals["mdot_in"] = ctx.signals.get(f"{active}__mdot_rin_to_cyl_kg_s", 0.0)
        ctx.signals["mdot_out"] = ctx.signals.get(f"{active}__mdot_cyl_to_rex_kg_s", 0.0)
        ctx.signals["A_in"] = ctx.signals.get(f"{active}__A_in_m2", 0.0)
        ctx.signals["A_ex"] = ctx.signals.get(f"{active}__A_ex_m2", 0.0)
        ctx.signals["qdot_combustion_W"] = ctx.signals.get(f"{active}__qdot_combustion_W", 0.0)
        ctx.signals["xb_combustion"] = ctx.signals.get(f"{active}__xb_combustion", 0.0)
        ctx.signals["dq_dtheta_combustion_J_per_deg"] = ctx.signals.get(
            f"{active}__dq_dtheta_combustion_J_per_deg",
            0.0,
        )

        # Globale Mehrzylinder-Sammelgrößen.
        ctx.signals["p_cyl_mean_pa"] = float(np.mean(p_list)) if p_list else 0.0
        ctx.signals["V_total_m3"] = float(np.sum(V_list)) if V_list else 0.0

        # Plenumzustände und Ein-/Auslass-Gesamtgrößen.
        ctx.signals["p_int_plenum_pa"] = p_int
        ctx.signals["T_int_plenum_K"] = T_int
        ctx.signals["m_int_plenum_kg"] = m_int
        ctx.signals["p_ex_plenum_pa"] = p_ex
        ctx.signals["T_ex_plenum_K"] = T_ex
        ctx.signals["m_ex_plenum_kg"] = m_ex
        ctx.signals["mdot_feed_int_kg_s"] = md_in_feed
        ctx.signals["mdot_discharge_ex_kg_s"] = md_ex_discharge

        # Drossel-/Feed-Diagnosegrößen.
        ctx.signals["A_throttle_m2"] = A_throttle
        ctx.signals["Cd_throttle"] = Cd_throttle
        ctx.signals["p_upstream_throttle_pa"] = p_src_in
        ctx.signals["T_upstream_throttle_K"] = T_src_in

        # Kompletten Ableitungsvektor an den Integrator zurückgeben.
        return dy
