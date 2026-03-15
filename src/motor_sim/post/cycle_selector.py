from __future__ import annotations

import numpy as np
import pandas as pd


def select_last_complete_cycles(df: pd.DataFrame, cycle_deg: float, n_cycles_store: int) -> tuple[pd.DataFrame, dict]:
    if df.empty:
        return df.copy(), {"theta_store_start_deg": 0.0, "theta_store_end_deg": 0.0, "n_cycles_store": int(n_cycles_store)}

    cycle_deg = float(cycle_deg)
    n_cycles_store = max(int(n_cycles_store), 1)

    theta_abs = df["theta_deg"].to_numpy(dtype=float)
    t_abs = df["t_s"].to_numpy(dtype=float) if "t_s" in df.columns else np.zeros(len(df), dtype=float)
    cycle_index_abs = np.floor(theta_abs / cycle_deg + 1e-12).astype(int)
    max_cycle_idx = int(np.max(cycle_index_abs))

    if float(np.max(theta_abs)) <= (max_cycle_idx * cycle_deg + 1e-9):
        last_complete_cycle_idx = max(max_cycle_idx - 1, 0)
    else:
        last_complete_cycle_idx = max_cycle_idx

    first_store_cycle_idx = max(0, last_complete_cycle_idx - n_cycles_store + 1)
    theta_store_start = first_store_cycle_idx * cycle_deg
    theta_store_end = theta_store_start + n_cycles_store * cycle_deg

    mask = (theta_abs >= theta_store_start - 1e-12) & (theta_abs < theta_store_end - 1e-12)
    out = df.loc[mask].copy()
    out.reset_index(drop=True, inplace=True)

    if out.empty:
        return out, {
            "theta_store_start_deg": float(theta_store_start),
            "theta_store_end_deg": float(theta_store_end),
            "n_cycles_store": int(n_cycles_store),
            "first_store_cycle_index": int(first_store_cycle_idx),
            "last_store_cycle_index": int(last_complete_cycle_idx),
        }

    out["theta_deg_abs"] = out["theta_deg"].astype(float)
    out["t_s_abs"] = out["t_s"].astype(float) if "t_s" in out.columns else 0.0
    out["cycle_index_abs"] = np.floor(out["theta_deg_abs"].to_numpy(dtype=float) / cycle_deg + 1e-12).astype(int)

    out["theta_deg"] = out["theta_deg_abs"].to_numpy(dtype=float) - float(theta_store_start)
    out["t_s"] = out["t_s_abs"].to_numpy(dtype=float) - float(out["t_s_abs"].iloc[0])
    out["theta_deg_cycle"] = np.mod(out["theta_deg"].to_numpy(dtype=float), cycle_deg)
    out["cycle_index"] = np.floor(out["theta_deg"].to_numpy(dtype=float) / cycle_deg + 1e-12).astype(int)

    meta = {
        "theta_store_start_deg": float(theta_store_start),
        "theta_store_end_deg": float(theta_store_end),
        "n_cycles_store": int(n_cycles_store),
        "first_store_cycle_index": int(first_store_cycle_idx),
        "last_store_cycle_index": int(last_complete_cycle_idx),
    }
    return out, meta
