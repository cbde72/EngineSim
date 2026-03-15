import numpy as np
def _trapz(y, x): return float(np.trapz(y, x)) if len(y) >= 2 else 0.0
def summarize_group_contributions(df, area_threshold_m2: float = 1e-7):
    out = {}; t = df["t_s"].to_numpy()
    Ain = df["A_in_m2"].to_numpy() if "A_in_m2" in df.columns else np.zeros_like(t)
    Aex = df["A_ex_m2"].to_numpy() if "A_ex_m2" in df.columns else np.zeros_like(t)
    scav_mask = (Ain > area_threshold_m2) & (Aex > area_threshold_m2)
    blow_mask = (Aex > area_threshold_m2) & (Ain <= area_threshold_m2)
    for c in df.columns:
        if c.endswith("_mdot_kg_s"):
            y = df[c].fillna(0.0).to_numpy(); base = c.replace("_mdot_kg_s", "")
            out[f"{base}_MASS_kg"] = _trapz(y, t)
            if base.startswith("INT_G"): out[f"{base}_SCAVENGE_MASS_kg"] = _trapz(y * scav_mask, t)
            if base.startswith("EXH_G"):
                out[f"{base}_BLOWDOWN_MASS_kg"] = _trapz(y * blow_mask, t)
                out[f"{base}_EXHAUST_MASS_kg"] = _trapz(y, t)
    out["area_threshold_m2"] = float(area_threshold_m2)
    return out
