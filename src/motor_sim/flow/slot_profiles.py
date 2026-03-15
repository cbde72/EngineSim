import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

@dataclass(frozen=True)
class SlotGeom:
    width_m: float
    height_m: float
    count: int
    offset_from_ut_m: float
    roof: Dict[str, Any]

    def _roof_len(self) -> float:
        roof = self.roof or {}
        rtype = str(roof.get("type", "none")).strip().lower()
        h = float(self.height_m)
        if rtype == "angle":
            angle_deg = float(roof.get("angle_deg", 0.0))
            L = float(self.width_m) * math.tan(math.radians(angle_deg))
            return _clamp(L, 0.0, h)
        return _clamp(float(roof.get("len_m", 0.0)), 0.0, h)

    def _area_per_slot(self, h_uncovered: float) -> float:
        w0 = float(self.width_m)
        h = float(self.height_m)
        hu = float(h_uncovered)
        roof = self.roof or {}
        rtype = str(roof.get("type", "none")).strip().lower()
        L = self._roof_len()

        if hu <= 0.0:
            return 0.0
        if rtype in ("none", "", "rect") or L <= 0.0:
            return w0 * hu
        if rtype == "factor":
            gamma = float(roof.get("gamma", 1.0))
            r = _clamp(hu / h, 0.0, 1.0)
            return w0 * hu * (r ** gamma)
        if rtype == "angle":
            rtype = "linear"

        z0 = h - L
        if hu <= z0:
            return w0 * hu

        A = w0 * z0
        u1 = _clamp((hu - z0) / L, 0.0, 1.0)
        if rtype == "linear":
            A += w0 * L * (u1 - 0.5 * u1 * u1)
            return A
        if rtype == "cos":
            A += w0 * L * 0.5 * (u1 + (1.0 / math.pi) * math.sin(math.pi * u1))
            return A
        return w0 * hu

    def area_open(self, y_from_ut_m: float) -> float:
        h = float(self.height_m)
        n = int(self.count)
        o = float(self.offset_from_ut_m)
        y = float(y_from_ut_m)
        h_uncovered = _clamp((o + h) - y, 0.0, h)
        return float(n) * self._area_per_slot(h_uncovered)

@dataclass(frozen=True)
class SlotGroup:
    geom: SlotGeom
    alphak_file: Optional[str] = None
    channel: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class SlotBank:
    groups: tuple[SlotGroup, ...]

@dataclass(frozen=True)
class SlotSet:
    intake: SlotBank
    exhaust: SlotBank
