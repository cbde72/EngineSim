"""Ventilereignisse aus Ventilhubsignalen ableiten.

Dieses Modul ist bewusst klein gehalten und kümmert sich nur um das Finden der
Öffnungs- und Schließwinkel aus zwei Hubsignalen:
- ``lift_in_mm``
- ``lift_ex_mm``

Aktuelles Verfahren
-------------------
Ein Ventil gilt als "offen", sobald sein Hub den gegebenen Schwellwert
überschreitet. Der erste und letzte Winkel oberhalb des Schwellwerts werden als
Öffnungs- bzw. Schließereignis interpretiert.

Grenzen des Verfahrens
----------------------
- keine Subsample-Interpolation an der Schwellwertkante
- keine Trennung mehrfacher Öffnungsfenster
- keine automatische Entfaltung bei 720°-Wrap-Around

Für viele technische Ventilkurven ist das ausreichend robust. Wenn später eine
präzisere Phasenbestimmung gewünscht ist, kann dieses Modul gut als Ort für
lineare Interpolation an der Schwellwertkante erweitert werden.
"""

from __future__ import annotations

import numpy as np


def find_open_close(theta_deg: np.ndarray, signal: np.ndarray, threshold: float) -> tuple[float | None, float | None]:
    """Bestimmt erstes und letztes Überschreiten eines Schwellwertes.

    Parameters
    ----------
    theta_deg:
        Winkelachse in Kurbelgrad.
    signal:
        Hubsignal oder allgemeines Öffnungssignal.
    threshold:
        Schwellwert für "geöffnet".

    Returns
    -------
    tuple[float | None, float | None]
        ``(open_deg, close_deg)``. Falls kein Wert oberhalb des Schwellwerts
        liegt, wird ``(None, None)`` geliefert.
    """
    if len(theta_deg) != len(signal):
        raise ValueError("theta_deg and signal must have the same length")

    above = np.asarray(signal) > float(threshold)
    if not np.any(above):
        return None, None

    idx = np.where(above)[0]
    return float(theta_deg[idx[0]]), float(theta_deg[idx[-1]])


def valve_events_from_lifts(df, lift_threshold_mm: float = 0.1) -> dict:
    """Extrahiert IVO/IVC/EVO/EVC aus einem Simulations-DataFrame.

    Erwartete DataFrame-Spalten:
    - ``theta_deg``
    - ``lift_in_mm``
    - ``lift_ex_mm``
    """
    required = {"theta_deg", "lift_in_mm", "lift_ex_mm"}
    if not required.issubset(df.columns):
        return {}

    theta = df["theta_deg"].to_numpy(dtype=float)
    lift_in = df["lift_in_mm"].to_numpy(dtype=float)
    lift_ex = df["lift_ex_mm"].to_numpy(dtype=float)

    ivo, ivc = find_open_close(theta, lift_in, lift_threshold_mm)
    evo, evc = find_open_close(theta, lift_ex, lift_threshold_mm)

    out = {"lift_threshold_mm": float(lift_threshold_mm)}
    if ivo is not None:
        out["IVO_deg"] = ivo
    if ivc is not None:
        out["IVC_deg"] = ivc
    if evo is not None:
        out["EVO_deg"] = evo
    if evc is not None:
        out["EVC_deg"] = evc
    return out
