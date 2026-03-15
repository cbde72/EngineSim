from __future__ import annotations

import numpy as np


def reference_points(cycle_deg: float = 720.0, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> dict[str, float]:
    cycle_deg = float(cycle_deg)
    mode = str(angle_ref_mode).upper().strip()
    if abs(cycle_deg - 720.0) > 1e-9:
        refs = {
            'firing_tdc_deg': 0.0,
            'gas_exchange_tdc_deg': 0.0,
            'power_bdc_deg': 180.0,
            'intake_bdc_deg': 180.0,
        }
    elif mode == 'GAS_EXCHANGE_TDC':
        refs = {
            'gas_exchange_tdc_deg': 0.0,
            'intake_bdc_deg': 180.0,
            'firing_tdc_deg': 360.0,
            'power_bdc_deg': 540.0,
        }
    else:
        refs = {
            'firing_tdc_deg': 0.0,
            'power_bdc_deg': 180.0,
            'gas_exchange_tdc_deg': 360.0,
            'intake_bdc_deg': 540.0,
        }

    offset = float(crank_angle_offset_deg)
    if abs(offset) <= 1e-12:
        return refs

    return {k: float(np.mod(v - offset, cycle_deg)) for k, v in refs.items()}


def ideal_phase_scalar(theta_deg: float, cycle_deg: float = 720.0, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0) -> str:
    mode = str(angle_ref_mode).upper().strip()
    th = float(np.mod(float(theta_deg) + float(crank_angle_offset_deg), cycle_deg))
    if abs(cycle_deg - 720.0) > 1e-9:
        return 'cycle'
    if mode == 'GAS_EXCHANGE_TDC':
        if 0.0 <= th < 180.0:
            return 'ansaugen'
        if 180.0 <= th < 360.0:
            return 'verdichten'
        if 360.0 <= th < 540.0:
            return 'arbeiten'
        return 'ausschieben'
    if 0.0 <= th < 180.0:
        return 'arbeiten'
    if 180.0 <= th < 360.0:
        return 'ausschieben'
    if 360.0 <= th < 540.0:
        return 'ansaugen'
    return 'verdichten'


def ideal_phase_array(theta_deg, cycle_deg: float = 720.0, angle_ref_mode: str = 'FIRE_TDC', crank_angle_offset_deg: float = 0.0):
    arr = np.asarray(theta_deg, dtype=float)
    return np.array([ideal_phase_scalar(v, cycle_deg, angle_ref_mode, crank_angle_offset_deg) for v in arr], dtype=object)
