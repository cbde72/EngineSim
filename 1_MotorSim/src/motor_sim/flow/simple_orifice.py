import math
def mdot_orifice(Cd, A, rho_up, dp):
    if A <= 0.0 or Cd <= 0.0:
        return 0.0
    if rho_up <= 0.0 or dp <= 0.0:
        return 0.0
    return Cd * A * math.sqrt(2.0 * rho_up * dp)
