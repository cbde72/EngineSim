import math
from motor_sim.flow.ports_profiles import AlphaK

class ValveAreaProvider:
    """
    Liefert wirksame Einlass-/Auslassflächen für ein Ventilmodell.

    Wichtige Definition
    -------------------
    alphaK ist hier als gesamtzylinderbezogener Kennwert interpretiert:

        A_eff,total = alphaK * A_piston

    also bezogen auf die Kolbenfläche des gesamten Zylinders und NICHT
    pro Einzelventil.

    Konsequenz:
    - count_in / count_ex geht in die gesamte geometrische Ventilsitzfläche
      ein und damit in alphaV.
    - count_in / count_ex wird NICHT zusätzlich auf alphaK * A_piston
      multipliziert, da dies alphaK doppelt skalieren würde.

    Damit gilt konsistent:

        A_eff,total = alphaK * A_piston
        alphaV      = A_eff,total / A_valve,total
    """

    def __init__(self, profiles, d_in_m, d_ex_m, count_in, count_ex, A_in_max, A_ex_max):
        self.prof = profiles
        self.d_in = float(d_in_m)
        self.d_ex = float(d_ex_m)
        self.count_in = max(int(count_in), 1)
        self.count_ex = max(int(count_ex), 1)
        self.A_in_max = float(A_in_max)
        self.A_ex_max = float(A_ex_max)

    @staticmethod
    def _seat_area(diameter_m: float) -> float:
        d = max(float(diameter_m), 0.0)
        return 0.25 * math.pi * d * d

    @staticmethod
    def _safe_positive(value: float, fallback: float = 0.0) -> float:
        try:
            v = float(value)
        except Exception:
            v = float(fallback)
        return max(v, 0.0)

    def eval(self, theta_deg, aux, ctx):
        lin, lex = self.prof.lifts_m(theta_deg)
        aKi, aKe = self.prof.alphak_from_lift(lin, lex)

        A_in_valve_single = self._seat_area(self.d_in)
        A_ex_valve_single = self._seat_area(self.d_ex)
        A_in_valve = self.count_in * A_in_valve_single
        A_ex_valve = self.count_ex * A_ex_valve_single
        A_piston = self._safe_positive(aux.get("A_piston_m2", 0.0))

        # Korrigierte alphaK-Interpretation:
        # alphaK ist auf die gesamte Kolbenfläche des Zylinders bezogen.
        A_in_eff = max(aKi, 0.0) * A_piston
        A_ex_eff = max(aKe, 0.0) * A_piston

        alphaV_in = (A_in_eff / A_in_valve) if A_in_valve > 0.0 else 0.0
        alphaV_ex = (A_ex_eff / A_ex_valve) if A_ex_valve > 0.0 else 0.0

        if ctx is not None and hasattr(ctx, "signals"):
            ctx.signals["valves__alphaK_in"] = float(max(aKi, 0.0))
            ctx.signals["valves__alphaK_ex"] = float(max(aKe, 0.0))
            ctx.signals["valves__alphaV_in"] = float(max(alphaV_in, 0.0))
            ctx.signals["valves__alphaV_ex"] = float(max(alphaV_ex, 0.0))
            ctx.signals["valves__count_in"] = float(self.count_in)
            ctx.signals["valves__count_ex"] = float(self.count_ex)
            ctx.signals["valves__A_in_valve_single_m2"] = float(A_in_valve_single)
            ctx.signals["valves__A_ex_valve_single_m2"] = float(A_ex_valve_single)
            ctx.signals["valves__A_in_valve_m2"] = float(A_in_valve)
            ctx.signals["valves__A_ex_valve_m2"] = float(A_ex_valve)
            ctx.signals["valves__A_piston_m2"] = float(A_piston)
            ctx.signals["valves__A_in_eff_m2"] = float(A_in_eff)
            ctx.signals["valves__A_ex_eff_m2"] = float(A_ex_eff)

        # alphaK ist bereits in A_eff eingerechnet.
        Cd_in = 1.0 if A_in_eff > 0.0 else 0.0
        Cd_ex = 1.0 if A_ex_eff > 0.0 else 0.0
        return A_in_eff, Cd_in, A_ex_eff, Cd_ex, lin, lex


class PortsAreaProvider:
    def __init__(self, area_table, alphak_table):
        self.area_table = area_table
        self.ak = alphak_table

    def eval(self, theta_deg, aux, ctx):
        A_in, A_ex = self.area_table.area(theta_deg)
        Cd_in, Cd_ex = self.ak.eval(theta_deg)
        return A_in, max(Cd_in, 0.0), A_ex, max(Cd_ex, 0.0), 0.0, 0.0


class SlotsAreaProvider:
    def __init__(self, slots, default_alphak_file):
        self.slots = slots
        self.default_ak = AlphaK.from_file(default_alphak_file)
        self.ak_cache = {default_alphak_file: self.default_ak}

    def _ak(self, path):
        if path is None:
            return self.default_ak
        if path not in self.ak_cache:
            self.ak_cache[path] = AlphaK.from_file(path)
        return self.ak_cache[path]

    @staticmethod
    def _channel_phi(channel: dict | None) -> float:
        if not channel:
            return 1.0
        zeta_local = float(channel.get("zeta_local", 0.0))
        friction_factor = float(channel.get("friction_factor", 0.0))
        length_m = float(channel.get("length_m", 0.0))
        dh_m = max(float(channel.get("hydraulic_diameter_m", 0.0)), 1e-9)
        phi_min = float(channel.get("phi_min", 0.2))
        zeta_total = max(0.0, zeta_local + friction_factor * length_m / dh_m)
        phi = 1.0 / math.sqrt(1.0 + zeta_total)
        return max(phi_min, min(1.0, phi))

    def _group_side(self, groups, theta_deg, y_from_ut_m, side, ctx, prefix):
        A_eff = 0.0
        for i, grp in enumerate(groups):
            A = float(grp.geom.area_open(y_from_ut_m))
            ak = self._ak(grp.alphak_file)
            a_in, a_ex = ak.eval(theta_deg)
            Cd = float(a_in if side == "in" else a_ex)
            phi = self._channel_phi(getattr(grp, "channel", None))
            ctx.signals[f"{prefix}{i+1}_A_geom_m2"] = A
            ctx.signals[f"{prefix}{i+1}_A_eff_m2"] = max(Cd, 0.0) * max(A, 0.0)
            ctx.signals[f"{prefix}{i+1}_channel_phi"] = phi
            A_eff += max(Cd, 0.0) * max(A, 0.0)
        return A_eff

    def eval(self, theta_deg, aux, ctx):
        x = float(aux.get("x", 0.0))
        stroke = float(getattr(ctx.kin, "stroke", 0.0))
        y_from_ut = max(0.0, stroke - x)

        A_in_eff = self._group_side(self.slots.intake.groups, theta_deg, y_from_ut, "in", ctx, "INT_G")
        A_ex_eff = self._group_side(self.slots.exhaust.groups, theta_deg, y_from_ut, "ex", ctx, "EXH_G")
        return A_in_eff, 1.0, A_ex_eff, 1.0, 0.0, 0.0
