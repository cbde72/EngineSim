from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple
import numpy as np

from .table_io import load_3col, load_4col

def classic_to_abs_deg(ref_deg: float, mode: str, deg: float) -> float:
    mode_u = mode.upper().strip()
    ref_deg = float(ref_deg)
    deg = float(deg)
    if mode_u in ("BTDC", "BBDC"):
        return ref_deg - deg
    if mode_u in ("ATDC", "ABDC"):
        return ref_deg + deg
    raise ValueError(f"Unknown classic timing mode: {mode}")

def make_periodic_table(theta_deg: np.ndarray, y: np.ndarray, cycle_deg: float) -> Tuple[np.ndarray, np.ndarray]:
    th = np.mod(np.asarray(theta_deg, dtype=float), cycle_deg)
    yy = np.asarray(y, dtype=float)

    order = np.argsort(th)
    th = th[order]
    yy = yy[order]

    th_u, idx = np.unique(th, return_index=True)
    th = th_u
    yy = yy[idx]

    if th.size < 2:
        raise ValueError("Need at least 2 distinct theta points for periodic interpolation.")

    th_ext = np.concatenate([th, [th[0] + cycle_deg]])
    y_ext  = np.concatenate([yy, [yy[0]]])
    return th_ext, y_ext

def interp_periodic(theta_query_deg: float, th_ext: np.ndarray, y_ext: np.ndarray, cycle_deg: float) -> float:
    tq = float(np.mod(theta_query_deg, cycle_deg))
    return float(np.interp(tq, th_ext, y_ext))

def _effective_window(theta_deg: np.ndarray, lift_m: np.ndarray, thr_m: float) -> tuple[float, float] | None:
    th = np.asarray(theta_deg, dtype=float)
    li = np.asarray(lift_m, dtype=float)
    mask = li > float(thr_m)
    if not np.any(mask):
        return None
    th_eff = th[mask]
    return float(np.min(th_eff)), float(np.max(th_eff))

def scale_theta_about_first(theta_deg: np.ndarray, angle_scale: float) -> np.ndarray:
    """Scale theta about first sample (legacy)."""
    th = np.asarray(theta_deg, dtype=float)
    s = float(angle_scale)
    th0 = float(th[0])
    return th0 + s * (th - th0)

def scale_theta_about_center(theta_deg: np.ndarray, angle_scale: float) -> np.ndarray:
    """Scale theta about the center of the valve-duration window.

    Center is computed from the min/max of the provided theta array.
    This is robust even if the table is not strictly sorted.
    """
    th = np.asarray(theta_deg, dtype=float)
    s = float(angle_scale)
    th_min = float(np.min(th))
    th_max = float(np.max(th))
    c = 0.5 * (th_min + th_max)
    return c + s * (th - c)

def scale_theta_about_effective_center(theta_deg: np.ndarray, lift_m: np.ndarray, angle_scale: float, thr_m: float) -> np.ndarray:
    """Scale theta about the center of the *effective* opening phase (lift > threshold)."""
    th = np.asarray(theta_deg, dtype=float)
    win = _effective_window(th, lift_m, thr_m)
    if win is None:
        # fallback: geometric center
        return scale_theta_about_center(th, angle_scale)
    th0, th1 = win
    c = 0.5 * (th0 + th1)
    s = float(angle_scale)
    return c + s * (th - c)

@dataclass
class ValveProfilesPeriodic:
    cycle_deg: float
    th_in_ext: np.ndarray
    lift_in_m_ext: np.ndarray
    th_ex_ext: np.ndarray
    lift_ex_m_ext: np.ndarray
    lift_ak_m: np.ndarray
    ak_in_by_lift: np.ndarray
    ak_ex_by_lift: np.ndarray
    ivo_abs_deg: float
    evo_abs_deg: float

    @staticmethod
    def from_files(
        lift_file: str,
        alphak_file: str,
        intake_open: Dict[str, Any],
        exhaust_open: Dict[str, Any],
        scaling: Dict[str, Any] | None = None,
        lift_angle_basis: str = "cam",
        cam_to_crank_ratio: float = 2.0,
        effective_lift_threshold_mm: float = 0.1,
        cycle_deg: float = 720.0,
    ) -> "ValveProfilesPeriodic":

        cycle_deg = float(cycle_deg)

        th_in, lift_in_mm, th_ex, lift_ex_mm = load_4col(lift_file)

        # --- input angles: cam-deg or crank-deg ---
        basis = str(lift_angle_basis).strip().lower()
        ratio = float(cam_to_crank_ratio)
        if basis == "cam":
            th_in = ratio * np.asarray(th_in, dtype=float)
            th_ex = ratio * np.asarray(th_ex, dtype=float)
        elif basis == "crank":
            th_in = np.asarray(th_in, dtype=float)
            th_ex = np.asarray(th_ex, dtype=float)
        else:
            raise ValueError(f"lift_angle_basis must be 'cam' or 'crank', got: {lift_angle_basis}")

        ivo_abs = classic_to_abs_deg(intake_open["ref_deg"], intake_open["mode"], intake_open["deg"])
        evo_abs = classic_to_abs_deg(exhaust_open["ref_deg"], exhaust_open["mode"], exhaust_open["deg"])

        # --- optional scaling (angle + lift) ---
        scaling = scaling or {}
        si = scaling.get("intake", {})
        se = scaling.get("exhaust", {})
        s_in_ang  = float(si.get("angle_scale", 1.0))
        s_in_lift = float(si.get("lift_scale", 1.0))
        s_ex_ang  = float(se.get("angle_scale", 1.0))
        s_ex_lift = float(se.get("lift_scale", 1.0))

        thr_m = 1e-3 * float(effective_lift_threshold_mm)
        lift_in_m = (1e-3 * np.asarray(lift_in_mm, dtype=float)) * s_in_lift
        lift_ex_m = (1e-3 * np.asarray(lift_ex_mm, dtype=float)) * s_ex_lift

        # First scale, then shift to the requested target event.
        # This keeps the final aligned opening/closing angle exact even when angle_scale != 1.
        th_in = scale_theta_about_effective_center(th_in, lift_in_m, s_in_ang, thr_m)
        th_ex = scale_theta_about_effective_center(th_ex, lift_ex_m, s_ex_ang, thr_m)

        def _shift_for_event(th_deg: np.ndarray, lift_m: np.ndarray, target_abs_deg: float, align: str) -> np.ndarray:
            th = np.asarray(th_deg, dtype=float)
            li = np.asarray(lift_m, dtype=float)
            align_u = str(align).strip().lower()
            win = _effective_window(th, li, thr_m)
            if win is None:
                th_open = float(th[0])
                th_close = float(th[-1])
            else:
                th_open, th_close = win
            ref = th_open if align_u == "open" else th_close
            return th + (float(target_abs_deg) - float(ref))

        th_in = _shift_for_event(th_in, lift_in_m, ivo_abs, intake_open.get("align", "open"))
        th_ex = _shift_for_event(th_ex, lift_ex_m, evo_abs, exhaust_open.get("align", "open"))

        th_in_ext, lift_in_m_ext = make_periodic_table(th_in, lift_in_m, cycle_deg)
        th_ex_ext, lift_ex_m_ext = make_periodic_table(th_ex, lift_ex_m, cycle_deg)

        # Valve alphaK table is lift-based:
        # x  = valve lift
        # y1 = alphaK intake
        # y2 = alphaK exhaust
        lift_ak_raw, aKi, aKe = load_3col(alphak_file)
        lift_ak_m = 1e-3 * np.asarray(lift_ak_raw, dtype=float)
        order_ak = np.argsort(lift_ak_m)
        lift_ak_m = lift_ak_m[order_ak]
        aKi = np.asarray(aKi, dtype=float)[order_ak]
        aKe = np.asarray(aKe, dtype=float)[order_ak]
        lift_ak_m, idx_ak = np.unique(lift_ak_m, return_index=True)
        aKi = aKi[idx_ak]
        aKe = aKe[idx_ak]
        if lift_ak_m.size < 2:
            raise ValueError(f"Need at least 2 distinct valve-lift alphaK points in {alphak_file}")

        return ValveProfilesPeriodic(
            cycle_deg=cycle_deg,
            th_in_ext=th_in_ext,
            lift_in_m_ext=lift_in_m_ext,
            th_ex_ext=th_ex_ext,
            lift_ex_m_ext=lift_ex_m_ext,
            lift_ak_m=lift_ak_m,
            ak_in_by_lift=aKi,
            ak_ex_by_lift=aKe,
            ivo_abs_deg=float(np.mod(ivo_abs, cycle_deg)),
            evo_abs_deg=float(np.mod(evo_abs, cycle_deg)),
        )

    def lifts_m(self, theta_deg: float):
        lin = interp_periodic(theta_deg, self.th_in_ext, self.lift_in_m_ext, self.cycle_deg)
        lex = interp_periodic(theta_deg, self.th_ex_ext, self.lift_ex_m_ext, self.cycle_deg)
        return lin, lex

    def alphak_from_lift(self, lift_in_m: float, lift_ex_m: float):
        li = max(float(lift_in_m), 0.0)
        le = max(float(lift_ex_m), 0.0)
        aKi = float(np.interp(li, self.lift_ak_m, self.ak_in_by_lift, left=self.ak_in_by_lift[0], right=self.ak_in_by_lift[-1]))
        aKe = float(np.interp(le, self.lift_ak_m, self.ak_ex_by_lift, left=self.ak_ex_by_lift[0], right=self.ak_ex_by_lift[-1]))
        return aKi, aKe
