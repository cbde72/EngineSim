# nozzle_choked.py

## Purpose

This module computes compressible nozzle mass flow.

## Functions

### `mdot_nozzle(...)`

Returns a positive mass-flow magnitude from upstream to downstream.
No reverse direction is represented here.

### `mdot_nozzle_signed(...)`

Returns a signed mass flow between two states.

- positive: state 1 -> state 2
- negative: state 2 -> state 1

## Physics

The model uses the standard isentropic nozzle relations and automatically
switches between subcritical and choked flow.

This is the key enabler for:

- intake reversion
- exhaust blowback
- overlap backflow in a physically consistent way
