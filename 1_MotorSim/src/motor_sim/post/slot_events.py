"""Ableitung von Slot-/Port-Steuerzeiten aus effektiven Flächen.

Das Modul wertet globale Flächen und optional gruppenspezifische Flächen aus.
Zentrale Ausgaben sind zum Beispiel:
- ``INT_OPEN_deg`` / ``INT_CLOSE_deg``
- ``EXH_OPEN_deg`` / ``EXH_CLOSE_deg``
- Gruppenevents wie ``INT_G1_OPEN_deg``
- Blowdown-Größen zwischen Abgas- und Einlassöffnung

Es handelt sich um eine pragmatische Schwellwert-Auswertung. Für viele
Port-Zeitdiagramme ist das ausreichend und nachvollziehbar.
"""

from __future__ import annotations

import re

import numpy as np


def _find_open_close(theta_deg: np.ndarray, area: np.ndarray, threshold: float) -> tuple[float | None, float | None]:
    """Liefert ersten und letzten Winkel oberhalb eines Flächenschwellwerts."""
    if len(theta_deg) != len(area):
        raise ValueError("theta_deg and area must have the same length")

    mask = np.asarray(area) > float(threshold)
    if not np.any(mask):
        return None, None

    idx = np.where(mask)[0]
    return float(theta_deg[idx[0]]), float(theta_deg[idx[-1]])


def summarize_slot_events(df, area_threshold_m2: float = 1e-7, per_group: bool = True) -> dict:
    """Erstellt eine Zusammenfassung der Port-/Slot-Ereignisse.

    Parameters
    ----------
    df:
        Simulations-DataFrame mit ``theta_deg`` und mindestens globalen
        Flächenspalten.
    area_threshold_m2:
        Schwellwert für "Port offen".
    per_group:
        Wenn ``True``, werden zusätzlich gruppenspezifische Öffnungen ermittelt.
    """
    if "theta_deg" not in df.columns:
        return {"area_threshold_m2": float(area_threshold_m2)}

    out: dict = {}
    theta = df["theta_deg"].to_numpy(dtype=float)

    for col, prefix in (("A_in_m2", "INT"), ("A_ex_m2", "EXH")):
        if col in df.columns:
            open_deg, close_deg = _find_open_close(theta, df[col].to_numpy(dtype=float), area_threshold_m2)
            if open_deg is not None:
                out[f"{prefix}_OPEN_deg"] = open_deg
                out[f"{prefix}_CLOSE_deg"] = close_deg
                out[f"{prefix}_DURATION_deg"] = max(0.0, close_deg - open_deg)

    intake_groups: dict[int, float] = {}
    exhaust_groups: dict[int, float] = {}

    if per_group:
        for col in df.columns:
            if col.endswith("_A_eff_m2") and (col.startswith("INT_G") or col.startswith("EXH_G")):
                prefix = col.replace("_A_eff_m2", "")
                open_deg, close_deg = _find_open_close(theta, df[col].to_numpy(dtype=float), area_threshold_m2)
                if open_deg is None:
                    continue

                out[f"{prefix}_OPEN_deg"] = open_deg
                out[f"{prefix}_CLOSE_deg"] = close_deg
                out[f"{prefix}_DURATION_deg"] = max(0.0, close_deg - open_deg)

                match = re.match(r"(INT_G|EXH_G)(\d+)", prefix)
                if match:
                    group_index = int(match.group(2))
                    if prefix.startswith("INT_G"):
                        intake_groups[group_index] = open_deg
                    else:
                        exhaust_groups[group_index] = open_deg

    if "EXH_OPEN_deg" in out and "INT_OPEN_deg" in out:
        out["BLOWDOWN_deg"] = out["INT_OPEN_deg"] - out["EXH_OPEN_deg"]

    for idx_int, int_open in intake_groups.items():
        for idx_exh, exh_open in exhaust_groups.items():
            out[f"BLOWDOWN_G{idx_exh}_TO_G{idx_int}_deg"] = int_open - exh_open

    out["area_threshold_m2"] = float(area_threshold_m2)
    return out
