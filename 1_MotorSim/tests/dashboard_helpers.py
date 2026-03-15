from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class CycleMetrics:
    pmax_bar: float
    theta_pmax_deg: float
    pmin_bar: float
    vmin_cm3: float
    vmax_cm3: float
    work_ind_j: float
    mdot_in_peak: float
    mdot_out_peak: float
    p_int_mean_bar: float
    p_ex_mean_bar: float


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode("ascii")
    plt.close(fig)
    return data


def compute_cycle_metrics(cur: dict) -> CycleMetrics:
    p_pa = np.asarray(cur["p_pa"])
    V_m3 = np.asarray(cur["V_m3"])
    mdot_in = np.asarray(cur["mdot_in"])
    mdot_out = np.asarray(cur["mdot_out"])
    p_int = np.asarray(cur["p_int_plenum_pa"])
    p_ex = np.asarray(cur["p_ex_plenum_pa"])
    theta_deg = np.asarray(cur["theta_deg"])

    i_pmax = int(np.argmax(p_pa))
    mdot_out_peak = float(np.max(np.abs(mdot_out))) if mdot_out.size else 0.0

    return CycleMetrics(
        pmax_bar=float(np.max(p_pa) / 1e5),
        theta_pmax_deg=float(theta_deg[i_pmax]),
        pmin_bar=float(np.min(p_pa) / 1e5),
        vmin_cm3=float(np.min(V_m3) * 1e6),
        vmax_cm3=float(np.max(V_m3) * 1e6),
        work_ind_j=float(np.trapezoid(p_pa, V_m3)),
        mdot_in_peak=float(np.max(np.abs(mdot_in))) if mdot_in.size else 0.0,
        mdot_out_peak=mdot_out_peak,
        p_int_mean_bar=float(np.mean(p_int) / 1e5),
        p_ex_mean_bar=float(np.mean(p_ex) / 1e5),
    )


def _status_cell(cur: float, ref: float, warn_rel: float, fail_rel: float, fmt: str = ".4f") -> str:
    if abs(ref) < 1e-15:
        rel = abs(cur - ref)
    else:
        rel = abs((cur - ref) / ref)

    if rel <= warn_rel:
        color = "#dff0d8"
    elif rel <= fail_rel:
        color = "#fcf8e3"
    else:
        color = "#f2dede"

    return (
        f'<td style="background:{color}; text-align:right;">{cur:{fmt}}</td>'
        f'<td style="text-align:right;">{ref:{fmt}}</td>'
        f'<td style="text-align:right;">{cur-ref:+{fmt}}</td>'
        f'<td style="text-align:right;">{100.0*rel:.3f}%</td>'
    )


def make_metrics_table(cur: dict, ref: dict | None = None) -> str:
    m_cur = compute_cycle_metrics(cur)
    rows: list[str] = []

    def add_row(label: str, cur_val: float, ref_val: float | None, unit: str,
                warn_rel: float = 0.002, fail_rel: float = 0.01, fmt: str = ".4f"):
        if ref_val is None:
            rows.append(
                f"<tr><td>{label}</td><td style='text-align:right;'>{cur_val:{fmt}}</td><td>{unit}</td></tr>"
            )
        else:
            cells = _status_cell(cur_val, ref_val, warn_rel, fail_rel, fmt=fmt)
            rows.append(f"<tr><td>{label} [{unit}]</td>{cells}</tr>")

    if ref is None:
        rows.append("<tr><th>Kennwert</th><th>Aktuell</th><th>Einheit</th></tr>")
        add_row("p_max", m_cur.pmax_bar, None, "bar")
        add_row("theta(p_max)", m_cur.theta_pmax_deg, None, "deg", fmt=".3f")
        add_row("p_min", m_cur.pmin_bar, None, "bar")
        add_row("V_min", m_cur.vmin_cm3, None, "cm3")
        add_row("V_max", m_cur.vmax_cm3, None, "cm3")
        add_row("integral p dV", m_cur.work_ind_j, None, "J", fmt=".6f")
        add_row("mdot_in_peak", m_cur.mdot_in_peak, None, "kg/s", fmt=".6e")
        add_row("mdot_out_peak", m_cur.mdot_out_peak, None, "kg/s", fmt=".6e")
        add_row("p_int_mean", m_cur.p_int_mean_bar, None, "bar")
        add_row("p_ex_mean", m_cur.p_ex_mean_bar, None, "bar")
    else:
        m_ref = compute_cycle_metrics(ref)
        rows.append("<tr><th>Kennwert</th><th>Aktuell</th><th>Referenz</th><th>Delta</th><th>Delta rel</th></tr>")
        add_row("p_max", m_cur.pmax_bar, m_ref.pmax_bar, "bar")
        add_row("theta(p_max)", m_cur.theta_pmax_deg, m_ref.theta_pmax_deg, "deg", warn_rel=0.0, fail_rel=0.01, fmt=".3f")
        add_row("p_min", m_cur.pmin_bar, m_ref.pmin_bar, "bar")
        add_row("V_min", m_cur.vmin_cm3, m_ref.vmin_cm3, "cm3", warn_rel=1e-6, fail_rel=1e-4)
        add_row("V_max", m_cur.vmax_cm3, m_ref.vmax_cm3, "cm3", warn_rel=1e-6, fail_rel=1e-4)
        add_row("integral p dV", m_cur.work_ind_j, m_ref.work_ind_j, "J", warn_rel=0.005, fail_rel=0.02, fmt=".6f")
        add_row("mdot_in_peak", m_cur.mdot_in_peak, m_ref.mdot_in_peak, "kg/s", warn_rel=0.01, fail_rel=0.05, fmt=".6e")
        add_row("mdot_out_peak", m_cur.mdot_out_peak, m_ref.mdot_out_peak, "kg/s", warn_rel=0.01, fail_rel=0.05, fmt=".6e")
        add_row("p_int_mean", m_cur.p_int_mean_bar, m_ref.p_int_mean_bar, "bar")
        add_row("p_ex_mean", m_cur.p_ex_mean_bar, m_ref.p_ex_mean_bar, "bar")

    return (
        '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; min-width:700px;">'
        + "".join(rows)
        + "</table>"
    )


def _single_plot(x, y, title, xlabel, ylabel, y_ref=None, label_cur="Aktuell", label_ref="Referenz") -> str:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(x, y, label=label_cur)
    if y_ref is not None:
        ax.plot(x, y_ref, label=label_ref)
        ax.legend()
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    return fig_to_base64(fig)


def pressure_plot(cur: dict, ref: dict | None = None) -> str:
    return _single_plot(
        cur["theta_deg"],
        np.asarray(cur["p_pa"]) / 1e5,
        "Zylinderdruck ueber Kurbelwinkel",
        "Kurbelwinkel [deg]",
        "Druck [bar]",
        None if ref is None else np.asarray(ref["p_pa"]) / 1e5,
    )


def pv_plot(cur: dict, ref: dict | None = None) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    ax.plot(np.asarray(cur["V_m3"]) * 1e6, np.asarray(cur["p_pa"]) / 1e5, label="Aktuell")
    if ref is not None:
        ax.plot(np.asarray(ref["V_m3"]) * 1e6, np.asarray(ref["p_pa"]) / 1e5, label="Referenz")
        ax.legend()
    ax.set_title("p-V-Diagramm")
    ax.set_xlabel("Volumen [cm3]")
    ax.set_ylabel("Druck [bar]")
    ax.grid(True)
    return fig_to_base64(fig)


def delta_pressure_plot(cur: dict, ref: dict) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.0))
    dp_bar = (np.asarray(cur["p_pa"]) - np.asarray(ref["p_pa"])) / 1e5
    ax.plot(cur["theta_deg"], dp_bar)
    ax.set_title("Druckabweichung zur Referenz")
    ax.set_xlabel("Kurbelwinkel [deg]")
    ax.set_ylabel("Delta p [bar]")
    ax.grid(True)
    return fig_to_base64(fig)


def massflow_plot(cur: dict, ref: dict | None = None) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(cur["theta_deg"], cur["mdot_in"], label="mdot_in aktuell")
    ax.plot(cur["theta_deg"], cur["mdot_out"], label="mdot_out aktuell")
    if ref is not None:
        ax.plot(ref["theta_deg"], ref["mdot_in"], linestyle="--", label="mdot_in Referenz")
        ax.plot(ref["theta_deg"], ref["mdot_out"], linestyle="--", label="mdot_out Referenz")
    ax.set_title("Massenstroeme")
    ax.set_xlabel("Kurbelwinkel [deg]")
    ax.set_ylabel("kg/s")
    ax.grid(True)
    ax.legend()
    return fig_to_base64(fig)


def combustion_plot(cur: dict, ref: dict | None = None) -> str:
    return _single_plot(
        cur["theta_deg"],
        np.asarray(cur["qdot_comb_W"]),
        "Verbrennungsfreisetzung",
        "Kurbelwinkel [deg]",
        "qdot [W]",
        None if ref is None else np.asarray(ref["qdot_comb_W"]),
    )


def plenums_plot(cur: dict, ref: dict | None = None) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(cur["theta_deg"], np.asarray(cur["p_int_plenum_pa"]) / 1e5, label="p_int aktuell")
    ax.plot(cur["theta_deg"], np.asarray(cur["p_ex_plenum_pa"]) / 1e5, label="p_ex aktuell")
    if ref is not None:
        ax.plot(ref["theta_deg"], np.asarray(ref["p_int_plenum_pa"]) / 1e5, linestyle="--", label="p_int Referenz")
        ax.plot(ref["theta_deg"], np.asarray(ref["p_ex_plenum_pa"]) / 1e5, linestyle="--", label="p_ex Referenz")
    ax.set_title("Plenendruecke")
    ax.set_xlabel("Kurbelwinkel [deg]")
    ax.set_ylabel("Druck [bar]")
    ax.grid(True)
    ax.legend()
    return fig_to_base64(fig)


def build_dashboard_html(cur: dict, ref: dict | None = None, title: str = "Engineering Test Dashboard") -> str:
    parts = [
        f"<h2>{title}</h2>",
        "<h3>Zyklus-Kennwerte</h3>",
        make_metrics_table(cur, ref),
        "<h3>Druckvergleich</h3>",
        f'<img src="data:image/png;base64,{pressure_plot(cur, ref)}" style="max-width:1100px;">',
        "<h3>p-V-Diagramm</h3>",
        f'<img src="data:image/png;base64,{pv_plot(cur, ref)}" style="max-width:900px;">',
        "<h3>Massenstroeme</h3>",
        f'<img src="data:image/png;base64,{massflow_plot(cur, ref)}" style="max-width:1100px;">',
        "<h3>Verbrennung</h3>",
        f'<img src="data:image/png;base64,{combustion_plot(cur, ref)}" style="max-width:1100px;">',
        "<h3>Plenendruecke</h3>",
        f'<img src="data:image/png;base64,{plenums_plot(cur, ref)}" style="max-width:1100px;">',
    ]
    if ref is not None:
        parts.extend([
            "<h3>Druckabweichung</h3>",
            f'<img src="data:image/png;base64,{delta_pressure_plot(cur, ref)}" style="max-width:1100px;">',
        ])
    return "<div>" + "\n".join(parts) + "</div>"
