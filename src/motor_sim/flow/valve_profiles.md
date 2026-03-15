# valve_profiles.py

## Purpose

This module maps crank angle to valve lift and valve lift to alphaK.

## Pipeline

1. Read intake/exhaust lift tables
2. Shift the curves to the requested absolute timing
3. Optionally scale duration and lift
4. Build periodic interpolation tables
5. Interpolate alphaK as a function of valve lift

## Important relation

The resulting lift values are passed to the valve area provider, where alphaK is
converted into an effective hydraulic area and alphaV diagnostics.

## Output

- `lifts_m(theta_deg)` -> intake and exhaust lift
- `alphak_from_lift(lift_in_m, lift_ex_m)` -> intake and exhaust alphaK
