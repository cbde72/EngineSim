"""Overlap-Berechnung aus Einlass- und Auslasshub.

Das Modul bestimmt Winkelsegmente, in denen sowohl Einlass als auch Auslass
oberhalb eines Schwellwertes liegen. Diese Information wird für:
- das Steuerzeiten-Diagramm
- den Steuerkreis
- Reporting und Timing-Summaries
verwendet.
"""

from __future__ import annotations

import numpy as np


def _segments_from_mask(theta_deg: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
    """Wandelt eine boolesche Öffnungsmaske in zusammenhängende Winkelintervalle um."""
    if len(theta_deg) != len(mask):
        raise ValueError("theta_deg and mask must have same length")
    if not np.any(mask):
        return []

    mask_int = mask.astype(int)
    dmask = np.diff(mask_int)
    starts = list(np.where(dmask == 1)[0] + 1)
    ends = list(np.where(dmask == -1)[0])

    if mask[0]:
        starts = [0] + starts
    if mask[-1]:
        ends = ends + [len(mask) - 1]

    return [(float(theta_deg[s]), float(theta_deg[e])) for s, e in zip(starts, ends)]


def valve_overlap_segments(df, lift_threshold_mm: float = 0.1) -> dict:
    """Berechnet Overlap-Segmente und Gesamtüberdeckung in Grad.

    Erwartete DataFrame-Spalten:
    - ``theta_deg``
    - ``lift_in_mm``
    - ``lift_ex_mm``
    """
    required = {"theta_deg", "lift_in_mm", "lift_ex_mm"}
    if not required.issubset(df.columns):
        return {"threshold_mm": float(lift_threshold_mm), "segments": [], "total_overlap_deg": 0.0}

    theta = df["theta_deg"].to_numpy(dtype=float)
    lift_in = df["lift_in_mm"].to_numpy(dtype=float)
    lift_ex = df["lift_ex_mm"].to_numpy(dtype=float)

    overlap_mask = (lift_in > lift_threshold_mm) & (lift_ex > lift_threshold_mm)
    segments = _segments_from_mask(theta, overlap_mask)
    total_deg = sum(max(0.0, end - start) for start, end in segments)

    return {
        "threshold_mm": float(lift_threshold_mm),
        "segments": segments,
        "total_overlap_deg": float(total_deg),
    }
