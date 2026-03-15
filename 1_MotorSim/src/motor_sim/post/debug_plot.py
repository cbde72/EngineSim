from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def write_debug_plot(df, out_dir: Path, cfg) -> Path | None:
    """Write an optional engineering debug figure controlled via config.

    Expected config block:
    {
      "enabled": true,
      "x_axis": "theta_deg",
      "dpi": 140,
      "filename": "out_debug.png"
    }
    """
    dbg = getattr(cfg, 'debug_plots', {}) if hasattr(cfg, 'debug_plots') else {}
    if not dbg or not bool(dbg.get('enabled', False)):
        return None

    x_col = str(dbg.get('x_axis', 'theta_deg'))
    if x_col not in df.columns:
        x_col = 'theta_deg' if 'theta_deg' in df.columns else df.columns[0]
    x = df[x_col].to_numpy(dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    if 'p' in df.columns:
        axes[0].plot(x, df['p'].to_numpy(dtype=float), label='p_cyl')
    if 'p_int_plenum_pa' in df.columns:
        axes[0].plot(x, df['p_int_plenum_pa'].to_numpy(dtype=float), label='p_int_plenum')
    if 'p_ex_plenum_pa' in df.columns:
        axes[0].plot(x, df['p_ex_plenum_pa'].to_numpy(dtype=float), label='p_ex_plenum')
    axes[0].set_ylabel('p [Pa]')
    axes[0].grid(True)
    axes[0].legend(loc='best')

    for col in ['mdot_int_signed_to_cyl_kg_s', 'mdot_ex_signed_to_cyl_kg_s', 'intake_reversion_kg_s', 'exhaust_blowback_kg_s']:
        if col in df.columns:
            axes[1].plot(x, df[col].to_numpy(dtype=float), label=col)
    axes[1].set_ylabel('ṁ [kg/s]')
    axes[1].grid(True)
    axes[1].legend(loc='best')

    plotted = False
    for col in ['alphaV_in', 'alphaV_ex', 'A_in', 'A_ex']:
        if col in df.columns:
            axes[2].plot(x, df[col].to_numpy(dtype=float), label=col)
            plotted = True
    if not plotted and 'valves__alphaV_in' in df.columns:
        axes[2].plot(x, df['valves__alphaV_in'].to_numpy(dtype=float), label='valves__alphaV_in')
        if 'valves__alphaV_ex' in df.columns:
            axes[2].plot(x, df['valves__alphaV_ex'].to_numpy(dtype=float), label='valves__alphaV_ex')
    axes[2].set_ylabel('alphaV / area')
    axes[2].set_xlabel(x_col)
    axes[2].grid(True)
    axes[2].legend(loc='best')

    fig.tight_layout()
    out = Path(out_dir) / str(dbg.get('filename', 'out_debug.png'))
    fig.savefig(out, dpi=int(dbg.get('dpi', 140)))
    plt.close(fig)
    return out
