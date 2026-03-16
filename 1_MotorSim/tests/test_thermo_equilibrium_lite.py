from motor_sim.gas.nasa7_library import complete_combustion_products
from motor_sim.gas.thermo import build_thermo_from_config
from motor_sim.config import load_config


def _atoms(comp):
    db = {
        "CO2": {"C": 1, "O": 2},
        "CO": {"C": 1, "O": 1},
        "H2O": {"H": 2, "O": 1},
        "H2": {"H": 2},
        "O2": {"O": 2},
        "OH": {"O": 1, "H": 1},
        "CH3OH": {"C": 1, "H": 4, "O": 1},
        "C2H5OH": {"C": 2, "H": 6, "O": 1},
    }
    out = {"C": 0.0, "H": 0.0, "O": 0.0}
    for name, n in comp.items():
        if name not in db:
            continue
        for el, coeff in db[name].items():
            out[el] += coeff * n
    return out


def test_equilibrium_lite_generates_shifted_species_but_preserves_atoms():
    base = complete_combustion_products("methanol", lambda_air=1.0, rich_mode="extended")
    shifted = complete_combustion_products(
        "methanol",
        lambda_air=1.0,
        rich_mode="extended",
        equilibrium_lite=True,
        equilibrium_temperature_K=2600.0,
        equilibrium_strength=0.6,
    )
    assert shifted.get("CO", 0.0) > base.get("CO", 0.0)
    assert shifted.get("H2", 0.0) > base.get("H2", 0.0)
    assert shifted.get("OH", 0.0) > 0.0
    a0 = _atoms(base)
    a1 = _atoms(shifted)
    for key in a0:
        assert abs(a0[key] - a1[key]) < 1e-9


def test_equilibrium_lite_low_temperature_is_effectively_off():
    base = complete_combustion_products("ethanol", lambda_air=1.1, rich_mode="extended")
    shifted = complete_combustion_products(
        "ethanol",
        lambda_air=1.1,
        rich_mode="extended",
        equilibrium_lite=True,
        equilibrium_temperature_K=900.0,
        equilibrium_strength=0.8,
    )
    assert shifted == base


def test_build_thermo_from_config_supports_equilibrium_lite_fields(tmp_path):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(
        """
{
  "case_name": "eq_lite",
  "engine": {
    "cycle_type": "4stroke",
    "rpm": 3000.0,
    "bore_m": 0.086,
    "stroke_m": 0.086,
    "conrod_m": 0.143,
    "compression_ratio": 10.0
  },
  "gas": {
    "thermo_mode": "nasa7_mixture",
    "mixture_preset": "combustion_products",
    "combustion_products_fuel_name": "methanol",
    "combustion_products_lambda": 1.0,
    "combustion_products_lambda_source": "config",
    "combustion_products_rich_mode": "extended",
    "combustion_products_equilibrium_lite_enabled": true,
    "combustion_products_equilibrium_lite_temperature_K": 2500.0,
    "combustion_products_equilibrium_lite_strength": 0.5
  },
  "manifolds": {
    "p_int_pa": 101325.0, "T_int_K": 300.0, "p_ex_pa": 101325.0, "T_ex_K": 800.0
  },
  "initial": {
    "p0_pa": 101325.0, "T0_K": 300.0
  },
  "simulation": {
    "t0_s": 0.0,
    "theta0_deg": 0.0,
    "n_cycles_store": 1,
    "n_cycles_compute": 1,
    "integrator": {"type": "rk4_fixed", "method": "RK45", "rtol": 1e-8, "atol": 1e-10, "max_step_s": 1e-4, "dt_internal_s": 1e-5},
    "output": {"dt_out_s": 1e-4, "dtheta_out_deg": 1.0},
    "live_plot": {"enabled": false, "every_n_out": 10, "window_s": 0.01}
  },
  "gasexchange": {"enabled": false, "mode": "valves", "flow_model": "nozzle_choked", "valves": {"lift_file": "data/valve_lift.txt", "alphak_file": "data/alphaK.txt", "d_in_m": 0.03, "d_ex_m": 0.03, "count_in": 1, "count_ex": 1, "A_in_port_max_m2": 1e-4, "A_ex_port_max_m2": 1e-4, "intake_open": {}, "exhaust_open": {}, "scaling": {}, "lift_angle_basis": "crank_deg", "cam_to_crank_ratio": 0.5, "effective_lift_threshold_mm": 0.0}, "ports": {"area_file": "data/ports_area.txt", "alphak_file": "data/alphaK_ports.txt"}, "slots": {"alphak_file": "data/alphaK_ports.txt", "intake": {"width_m": 0.001, "height_m": 0.001, "count": 1, "offset_from_ut_m": 0.0, "roof": {}, "alphak_file": null, "channel": {}}, "exhaust": {"width_m": 0.001, "height_m": 0.001, "count": 1, "offset_from_ut_m": 0.0, "roof": {}, "alphak_file": null, "channel": {}}, "intake_groups": [], "exhaust_groups": []}},
  "output_files": {"out_dir": "out", "csv_name": "out.csv", "plot_name": "plot.png"}
}
        """
    )
    cfg = load_config(str(cfg_path))
    thermo = build_thermo_from_config(cfg.gas, combustion_cfg={"lambda": 0.95})
    assert thermo.R > 100.0
    assert thermo.cp_mass(2200.0) > thermo.cv_mass(2200.0)


def test_build_thermo_from_config_supports_temperature_coupled_equilibrium_lite(tmp_path):
    cfg_path = tmp_path / "cfg_tempcoupled.json"
    cfg_path.write_text(
        """
{
  "case_name": "eq_lite_tempcoupled",
  "engine": {
    "cycle_type": "4stroke",
    "rpm": 3000.0,
    "bore_m": 0.086,
    "stroke_m": 0.086,
    "conrod_m": 0.143,
    "compression_ratio": 10.0
  },
  "gas": {
    "thermo_mode": "nasa7_mixture",
    "mixture_preset": "combustion_products",
    "combustion_products_fuel_name": "methanol",
    "combustion_products_lambda": 1.0,
    "combustion_products_lambda_source": "config",
    "combustion_products_rich_mode": "extended",
    "combustion_products_equilibrium_lite_enabled": true,
    "combustion_products_equilibrium_lite_temperature_source": "cylinder",
    "combustion_products_equilibrium_lite_temperature_min_K": 1200.0,
    "combustion_products_equilibrium_lite_temperature_max_K": 3000.0,
    "combustion_products_equilibrium_lite_strength": 0.6
  },
  "manifolds": {
    "p_int_pa": 101325.0, "T_int_K": 300.0, "p_ex_pa": 101325.0, "T_ex_K": 800.0
  },
  "initial": {
    "p0_pa": 101325.0, "T0_K": 300.0
  },
  "simulation": {
    "t0_s": 0.0,
    "theta0_deg": 0.0,
    "n_cycles_store": 1,
    "n_cycles_compute": 1,
    "integrator": {"type": "rk4_fixed", "method": "RK45", "rtol": 1e-8, "atol": 1e-10, "max_step_s": 1e-4, "dt_internal_s": 1e-5},
    "output": {"dt_out_s": 1e-4, "dtheta_out_deg": 1.0},
    "live_plot": {"enabled": false, "every_n_out": 10, "window_s": 0.01}
  },
  "gasexchange": {"enabled": false, "mode": "valves", "flow_model": "nozzle_choked", "valves": {"lift_file": "data/valve_lift.txt", "alphak_file": "data/alphaK.txt", "d_in_m": 0.03, "d_ex_m": 0.03, "count_in": 1, "count_ex": 1, "A_in_port_max_m2": 1e-4, "A_ex_port_max_m2": 1e-4, "intake_open": {}, "exhaust_open": {}, "scaling": {}, "lift_angle_basis": "crank_deg", "cam_to_crank_ratio": 0.5, "effective_lift_threshold_mm": 0.0}, "ports": {"area_file": "data/ports_area.txt", "alphak_file": "data/alphaK_ports.txt"}, "slots": {"alphak_file": "data/alphaK_ports.txt", "intake": {"width_m": 0.001, "height_m": 0.001, "count": 1, "offset_from_ut_m": 0.0, "roof": {}, "alphak_file": null, "channel": {}}, "exhaust": {"width_m": 0.001, "height_m": 0.001, "count": 1, "offset_from_ut_m": 0.0, "roof": {}, "alphak_file": null, "channel": {}}, "intake_groups": [], "exhaust_groups": []}},
  "output_files": {"out_dir": "out", "csv_name": "out.csv", "plot_name": "plot.png"}
}
        """
    )
    cfg = load_config(str(cfg_path))
    thermo = build_thermo_from_config(cfg.gas, combustion_cfg={"lambda": 1.0})
    cp_cold = thermo.cp_mass(1200.0)
    cp_hot = thermo.cp_mass(2800.0)
    r_cold = thermo.R_at(1200.0)
    r_hot = thermo.R_at(2800.0)
    assert cp_hot != cp_cold
    assert r_hot >= r_cold
    assert thermo.p_from_mTV(0.001, 2800.0, 1e-3) > thermo.p_from_mTV(0.001, 1200.0, 1e-3)
