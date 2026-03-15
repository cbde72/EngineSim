# model.py signed-flow notes

## Cylinder sign convention

The solver now uses one explicit convention:

- positive mass flow: into the cylinder
- negative mass flow: out of the cylinder

## Intake and exhaust port states

The intake port is defined with `direction='to_cylinder'`.
The exhaust port is defined with `direction='from_cylinder'`.

This means the solver can distinguish:

- normal intake flow
- intake reversion
- normal exhaust discharge
- exhaust blowback

## Energy balance

The cylinder energy equation uses the upstream temperature corresponding to the
actual flow direction. That keeps the `mdot*h` term consistent during backflow.

## New diagnostics

For each cylinder the solver writes:

- `__mdot_int_signed_to_cyl_kg_s`
- `__mdot_ex_signed_to_cyl_kg_s`
- `__intake_reversion_kg_s`
- `__exhaust_blowback_kg_s`
- `__alphaV_in`
- `__alphaV_ex`
