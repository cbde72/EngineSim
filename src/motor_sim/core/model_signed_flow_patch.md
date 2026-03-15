# Signed-flow patch for `core/model.py`

This patch makes the active solver path truly bidirectional.

## Main changes

1. `flow/nozzle_choked.py`
   - adds `mdot_nozzle_signed(...)`
   - positive means state 1 -> state 2
   - negative means state 2 -> state 1

2. `core/model.py`
   - replaces the old unsigned `_flow()` path with `_signed_flow_ab(...)`
   - uses `PortDefinition` + `signed_port_mdot(...)` for intake and exhaust ports
   - applies cylinder sign convention:
     - positive = into cylinder
     - negative = out of cylinder

3. Cylinder balances
   - mass balance now uses signed port fluxes directly:
     `dm_dt = md_int_to_cyl + md_ex_to_cyl`
   - exhaust normal outflow therefore appears as negative exhaust-port flux
   - exhaust blowback appears as positive exhaust-port flux
   - intake reversion appears as negative intake-port flux

4. New diagnostics
   - `__mdot_intake_to_cyl_kg_s`
   - `__mdot_exhaust_to_cyl_kg_s`
   - `__intake_reversion_kg_s`
   - `__exhaust_blowback_kg_s`
   - `__intake_flow_direction`
   - `__exhaust_flow_direction`

## Notes

The generic signals `mdot_in` and `mdot_out` are now both in cylinder sign convention.
That means `mdot_out` is negative during normal exhaust outflow and positive during blowback.
