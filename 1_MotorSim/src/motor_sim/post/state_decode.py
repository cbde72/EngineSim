from __future__ import annotations

import numpy as np
import pandas as pd


def gas_cv(gas_R: float, gas_cp: float) -> float:
    return float(gas_cp) - float(gas_R)


def temperature_from_mass_energy(mass_kg: float, internal_energy_J: float, gas_R: float, gas_cp: float, *, min_mass_kg: float = 1.0e-12, min_temp_K: float = 1.0e-9) -> float:
    cv = gas_cv(gas_R, gas_cp)
    m = max(float(mass_kg), float(min_mass_kg))
    T = float(internal_energy_J) / max(m * cv, 1.0e-30)
    return max(float(min_temp_K), T)


def internal_energy_from_mass_temp(mass_kg: float, temp_K: float, gas_R: float, gas_cp: float) -> float:
    return float(mass_kg) * gas_cv(gas_R, gas_cp) * float(temp_K)


def _series_or_none(df: pd.DataFrame, name: str):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").to_numpy(dtype=float)
    return None


def temperature_series_from_columns(df: pd.DataFrame, *, mass_col: str, temp_col: str | None, energy_col: str | None, gas_R: float, gas_cp: float, default_K: float = 300.0) -> np.ndarray:
    temp = _series_or_none(df, temp_col) if temp_col else None
    if temp is not None:
        return temp
    mass = _series_or_none(df, mass_col)
    energy = _series_or_none(df, energy_col) if energy_col else None
    if mass is not None and energy is not None:
        cv = gas_cv(gas_R, gas_cp)
        denom = np.maximum(mass * cv, 1.0e-30)
        return np.maximum(1.0e-9, energy / denom)
    if mass is not None:
        return np.full_like(mass, float(default_K), dtype=float)
    return np.asarray([], dtype=float)


def scalar_temperature_from_rowlike(rowlike, *, mass_key: str, temp_key: str | None, energy_key: str | None, gas_R: float, gas_cp: float, default_K: float = 300.0) -> float:
    try:
        if temp_key and temp_key in rowlike and rowlike[temp_key] is not None:
            return float(rowlike[temp_key])
    except Exception:
        pass
    try:
        if mass_key and energy_key and energy_key in rowlike and rowlike[energy_key] is not None:
            return temperature_from_mass_energy(float(rowlike[mass_key]), float(rowlike[energy_key]), gas_R, gas_cp)
    except Exception:
        pass
    return float(default_K)


def detect_prefixes(df: pd.DataFrame, suffixes: tuple[str, ...]) -> list[str]:
    """Return sorted signal prefixes for column groups ending with one of `suffixes`.

    Example
    -------
    cyl1__m_rin_kg_state -> prefix ``cyl1`` for suffix ``__m_rin_kg_state``
    """
    prefixes: set[str] = set()
    for col in df.columns:
        for suffix in suffixes:
            if col.endswith(suffix):
                prefixes.add(col[:-len(suffix)])
                break
    return sorted(prefixes)


# Backward-compatible private alias used by older post-processing paths.
def _detect_prefixes(df: pd.DataFrame, suffixes: tuple[str, ...]) -> list[str]:
    return detect_prefixes(df, suffixes)
