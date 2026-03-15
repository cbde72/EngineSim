# debug_plot.py

## Purpose

Optional engineering debug plot controlled via config.

## Config block

```json
"debug_plots": {
  "enabled": true,
  "x_axis": "theta_deg",
  "dpi": 140,
  "filename": "out_debug.png"
}
```

## Contents

The plot shows:

1. cylinder and plenum pressures
2. signed intake/exhaust mass flow plus reversion/blowback
3. alphaV and effective areas

This plot is intended for rapid validation of gas-exchange behavior.
