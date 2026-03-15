import math

def throttle_area(diameter_m: float, position: float, position_mode: str = "fraction", A_max_m2: float = 0.0) -> float:
    if float(A_max_m2) > 0.0:
        Amax = float(A_max_m2)
    else:
        d = max(float(diameter_m), 1e-12)
        Amax = math.pi * 0.25 * d * d

    if str(position_mode).lower() == "fraction":
        frac = max(0.0, min(1.0, float(position)))
        return Amax * frac
    # fallback: treat position as effective area fraction
    frac = max(0.0, min(1.0, float(position)))
    return Amax * frac
