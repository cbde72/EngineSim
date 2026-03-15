from dataclasses import dataclass
import math

@dataclass(frozen=True)
class PistonModel:
    bore_m: float
    area_scale: float = 1.0
    crown_temperature_K: float = 520.0

    @property
    def base_area_m2(self) -> float:
        return math.pi * (0.5 * float(self.bore_m)) ** 2

    @property
    def area_m2(self) -> float:
        return self.base_area_m2 * float(self.area_scale)

@dataclass(frozen=True)
class HeadModel:
    bore_m: float
    area_scale: float = 1.0
    wall_temperature_K: float = 480.0

    @property
    def base_area_m2(self) -> float:
        return math.pi * (0.5 * float(self.bore_m)) ** 2

    @property
    def area_m2(self) -> float:
        return self.base_area_m2 * float(self.area_scale)

@dataclass(frozen=True)
class LinerModel:
    bore_m: float
    stroke_m: float
    area_scale: float = 1.0
    wall_temperature_K: float = 430.0

    @property
    def circumference_m(self) -> float:
        return math.pi * float(self.bore_m)

    def wetted_area_m2(self, x_from_tdc_m: float) -> float:
        x = max(0.0, min(float(self.stroke_m), float(x_from_tdc_m)))
        return self.circumference_m * x * float(self.area_scale)

    def total_swept_wall_area_m2(self) -> float:
        return self.circumference_m * float(self.stroke_m) * float(self.area_scale)
