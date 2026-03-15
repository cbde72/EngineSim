import math

def mdot_nozzle(Cd, A, p_up, T_up, p_down, gamma, R):
    """Unsigned nozzle flow magnitude in the declared up -> down direction."""
    if A <= 0.0 or Cd <= 0.0:
        return 0.0
    if p_up <= 0.0 or T_up <= 0.0:
        return 0.0
    if p_down >= p_up:
        return 0.0

    pr = p_down / p_up
    pr_crit = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))

    if pr <= pr_crit:
        factor = (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        return Cd * A * p_up * math.sqrt(gamma / (R * T_up)) * factor

    term = (pr ** (2.0 / gamma) - pr ** ((gamma + 1.0) / gamma))
    if term <= 0.0:
        return 0.0
    return Cd * A * p_up * math.sqrt((2.0 * gamma / (R * T_up * (gamma - 1.0))) * term)


def mdot_nozzle_signed(Cd, A, p1, T1, p2, T2, gamma, R):
    """Signed nozzle flow.

    Positive means mass flows from state 1 -> state 2.
    Negative means mass flows from state 2 -> state 1.
    """
    if A <= 0.0 or Cd <= 0.0:
        return 0.0
    if p1 <= 0.0 or p2 <= 0.0:
        return 0.0
    if T1 <= 0.0 or T2 <= 0.0:
        return 0.0

    if p1 >= p2:
        sign = 1.0
        p_up, T_up, p_down = p1, T1, p2
    else:
        sign = -1.0
        p_up, T_up, p_down = p2, T2, p1

    mdot_mag = mdot_nozzle(Cd, A, p_up, T_up, p_down, gamma, R)
    return sign * mdot_mag
