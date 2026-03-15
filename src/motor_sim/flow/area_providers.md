# area_providers.py

## Purpose

This module converts geometry and alphaK/area tables into effective intake and
exhaust port definitions.

## Providers

### `ValveAreaProvider`

Uses lift profiles and alphaK tables.
The effective area follows the project convention:

`count * alphaK * A_piston = alphaV * A_valve,total = A_eff,total`

The provider also exposes `alphaV_in` and `alphaV_ex` as explicit diagnostic
signals.

### `PortsAreaProvider`

Uses direct area tables plus alphaK/Cd tables as a crank-angle based port model.

### `SlotsAreaProvider`

Builds effective slot areas and can apply channel loss factors.

## Unified output

All providers implement `eval_ports(...)` and return two `PortDefinition`
objects:

- intake port (`direction='to_cylinder'`)
- exhaust port (`direction='from_cylinder'`)

This creates a single solver interface for valves, ports and slots.
