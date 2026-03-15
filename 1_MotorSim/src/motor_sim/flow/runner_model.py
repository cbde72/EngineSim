import math

def area_from_diameter(diameter_m: float) -> float:
    d = max(float(diameter_m), 1e-12)
    return math.pi * 0.25 * d * d

def hydraulic_phi(length_m: float, diameter_m: float, zeta_local: float, friction_factor: float) -> float:
    d = max(float(diameter_m), 1e-12)
    loss = max(0.0, float(zeta_local)) + max(0.0, float(friction_factor)) * max(0.0, float(length_m)) / d
    return 1.0 / math.sqrt(max(1.0 + loss, 1e-12))

def effective_area(area_geom_m2: float, length_m: float, diameter_m: float, zeta_local: float, friction_factor: float) -> tuple[float, float]:
    phi = hydraulic_phi(length_m, diameter_m, zeta_local, friction_factor)
    return float(area_geom_m2) * phi, phi
