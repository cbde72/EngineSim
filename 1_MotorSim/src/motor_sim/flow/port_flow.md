# port_flow.py

## Purpose

This module introduces a unified port definition for the gas-exchange solver.
It standardizes how intake and exhaust ports are described before the solver
computes mass flow.

## Core object: `PortDefinition`

A port is described by:

- `name`: diagnostic label
- `direction`: relative to the cylinder
  - `to_cylinder`
  - `from_cylinder`
- `area_eff_m2`: effective hydraulic area
- `cd`: discharge coefficient
- `area_geom_m2`: optional geometric reference area
- `alpha_v`: optional valve flow coefficient
- `lift_m`: optional lift signal

This lets the solver use one interface for valves, ports and slots.

## Signed mass-flow convention

The module enforces a cylinder-based sign convention:

- positive: flow into the cylinder
- negative: flow out of the cylinder

This is implemented by `signed_port_mdot(...)`.

## Enthalpy handling

`enthalpy_from_signed_flow(...)` computes the cylinder energy term `mdot*h`
with the physically correct upstream temperature depending on the flow sign.

## Why this matters

This makes the solver able to represent:

- intake reversion
- exhaust blowback
- valve overlap with backflow
- one consistent interface across all gas-exchange actuation types
