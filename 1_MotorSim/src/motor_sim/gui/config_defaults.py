import copy

DEFAULT_CONFIG = {
    "case_name": "motor_sim_gui_demo",
    "engine": {
        "cycle_type": "4T",
        "rpm": 3000.0,
        "freq_hz": None,
        "bore_m": 0.086,
        "stroke_m": 0.086,
        "conrod_m": 0.143,
        "compression_ratio": 10.5
    },
    "gas": {
        "R_J_per_kgK": 287.0,
        "cp_J_per_kgK": 1005.0
    },
    "manifolds": {
        "p_int_pa": 100000.0,
        "T_int_K": 300.0,
        "p_ex_pa": 105000.0,
        "T_ex_K": 650.0
    },
    "initial": {
        "p0_pa": 100000.0,
        "T0_K": 300.0
    },
    "simulation": {
        "t0_s": 0.0,
        "theta0_deg": 0.0,
        "n_cycles_store": 2,
        "n_cycles_compute": 5,
        "integrator": {
            "type": "rk4_fixed",
            "method": "RK45",
            "rtol": 1e-8,
            "atol": 1e-10,
            "max_step_s": 1e-4,
            "dt_internal_s": 1e-5
        },
        "output": {
            "dt_out_s": 1e-4,
            "dtheta_out_deg": 0.5
        },
        "live_plot": {
            "enabled": False,
            "every_n_out": 5,
            "window_s": 0.02
        },
        "cycle_convergence": {
            "enabled": True,
            "rel_tol_mass": 1e-4,
            "rel_tol_temp": 5e-4,
            "abs_tol_mass_kg": 1e-8,
            "abs_tol_temp_K": 1e-3,
            "required_consecutive_cycles": 3,
            "min_cycles_before_check": 4,
            "stop_when_converged": True,
            "verbose": True,
            "monitored_states": [
                "cylinder_masses",
                "cylinder_temperatures",
                "imep",
                "fuel_mass_per_cycle",
                "intake_plenum_mass",
                "exhaust_plenum_mass",
                "intake_plenum_temperature",
                "exhaust_plenum_temperature"
            ],
            "rel_tol_other": 5e-4,
            "abs_tol_other": 1e-3
        }
    },
    "gasexchange": {
        "enabled": True,
        "mode": "slots",
        "flow_model": "nozzle_choked",
        "valves": {
            "lift_file": "data/valve_lift_4col.txt",
            "alphak_file": "data/alphaK.txt",
            "d_in_m": 0.032,
            "d_ex_m": 0.028,
            "count_in": 2,
            "count_ex": 2,
            "A_in_port_max_m2": 8.0e-4,
            "A_ex_port_max_m2": 7.0e-4,
            "intake_open": {"ref_deg": 360.0, "mode": "BTDC", "deg": 10.0, "align": "open"},
            "exhaust_open": {"ref_deg": 180.0, "mode": "BBDC", "deg": 40.0, "align": "open"},
            "scaling": {
                "intake": {"angle_scale": 1.0, "lift_scale": 1.0},
                "exhaust": {"angle_scale": 1.0, "lift_scale": 1.0}
            },
            "lift_angle_basis": "crank",
            "cam_to_crank_ratio": 2.0,
            "effective_lift_threshold_mm": 0.1
        },
        "ports": {
            "area_file": "data/ports_area.txt",
            "alphak_file": "data/alphaK_ports.txt"
        },
        "slots": {
            "alphak_file": "data/alphaK_ports.txt",
            "intake": {
                "width_m": 0.010,
                "height_m": 0.020,
                "count": 8,
                "offset_from_ut_m": 0.015,
                "roof": {"type": "cos", "len_m": 0.004},
                "alphak_file": "data/alphaK_ports_boost.txt",
                "channel": {
                    "zeta_local": 1.0,
                    "friction_factor": 0.02,
                    "length_m": 0.03,
                    "hydraulic_diameter_m": 0.01,
                    "phi_min": 0.2
                }
            },
            "exhaust": {
                "width_m": 0.012,
                "height_m": 0.022,
                "count": 6,
                "offset_from_ut_m": 0.012,
                "roof": {"type": "cos", "len_m": 0.004},
                "alphak_file": "data/alphaK_ports_exhaust.txt",
                "channel": {
                    "zeta_local": 1.0,
                    "friction_factor": 0.02,
                    "length_m": 0.03,
                    "hydraulic_diameter_m": 0.01,
                    "phi_min": 0.2
                }
            },
            "intake_groups": [
                {
                    "width_m": 0.010,
                    "height_m": 0.020,
                    "count": 4,
                    "offset_from_ut_m": 0.015,
                    "roof": {"type": "angle", "angle_deg": 20.0},
                    "alphak_file": "data/alphaK_ports_boost.txt",
                    "channel": {
                        "zeta_local": 1.0,
                        "friction_factor": 0.02,
                        "length_m": 0.03,
                        "hydraulic_diameter_m": 0.01,
                        "phi_min": 0.2
                    }
                },
                {
                    "width_m": 0.008,
                    "height_m": 0.016,
                    "count": 4,
                    "offset_from_ut_m": 0.010,
                    "roof": {"type": "cos", "len_m": 0.003},
                    "alphak_file": "data/alphaK_ports_main.txt",
                    "channel": {
                        "zeta_local": 1.0,
                        "friction_factor": 0.02,
                        "length_m": 0.03,
                        "hydraulic_diameter_m": 0.01,
                        "phi_min": 0.2
                    }
                }
            ],
            "exhaust_groups": [
                {
                    "width_m": 0.012,
                    "height_m": 0.022,
                    "count": 6,
                    "offset_from_ut_m": 0.012,
                    "roof": {"type": "cos", "len_m": 0.004},
                    "alphak_file": "data/alphaK_ports_exhaust.txt",
                    "channel": {
                        "zeta_local": 1.0,
                        "friction_factor": 0.02,
                        "length_m": 0.03,
                        "hydraulic_diameter_m": 0.01,
                        "phi_min": 0.2
                    }
                }
            ]
        }
    },
    "output_files": {
        "out_dir": "out",
        "csv_name": "out_gui.csv",
        "plot_name": "out_gui.png"
    },

    "plena": {
        "enabled": True,
        "intake": {
            "volume_m3": 0.012,
            "p0_pa": 100000.0,
            "T0_K": 300.0
        },
        "exhaust": {
            "volume_m3": 0.018,
            "p0_pa": 105000.0,
            "T0_K": 650.0
        }
    },

    "throttle": {
        "enabled": True,
        "diameter_m": 0.032,
        "cd": 0.82,
        "position": 0.65,
        "position_mode": "fraction",
        "A_max_m2": 0.0,
        "T_upstream_K": 300.0,
        "p_upstream_pa": 101325.0
    },

    "energy_models": {
        "combustion": {
            "enabled": False,
            "heat_input_mode": "lambda",
            "ca50_rel_zuend_ot_deg": 8.0,
            "duration_deg": 40.0,
            "wiebe_a": 5.0,
            "wiebe_m": 2.0,
            "lambda": 1.0,
            "fuel_lhv_J_per_kg": 42500000.0,
            "fuel_afr_stoich_kg_air_per_kg_fuel": 14.7,
            "combustion_efficiency": 0.98,
            "q_total_J_per_cycle": 0.0
        },
        "wall_heat": {
            "enabled": False,
            "h_piston_W_m2K": 150.0,
            "h_head_W_m2K": 180.0,
            "h_liner_W_m2K": 130.0
        },
        "generator": {
            "enabled": False,
            "eta_mech_to_electric": 0.9,
            "positive_work_only": True
        }
    },

    "user_cylinders": [
        {
            "name": "user_cylinder_1",
            "enabled": True,
            "crank_angle_offset_deg": 0.0,
            "actuation_source": "auto",
            "notes": "Primary cylinder",
            "connections": {
                "intake_name": "intake_manifold_1",
                "exhaust_name": "exhaust_manifold_1"
            },
            "runners": {
                "intake": {
                    "length_m": 0.25,
                    "diameter_m": 0.035,
                    "volume_m3": 0.00024,
                    "zeta_local": 1.2,
                    "friction_factor": 0.03,
                    "wall_temperature_K": 320.0,
                    "enabled": True
                },
                "exhaust": {
                    "length_m": 0.35,
                    "diameter_m": 0.03,
                    "volume_m3": 0.00025,
                    "zeta_local": 1.8,
                    "friction_factor": 0.04,
                    "wall_temperature_K": 650.0,
                    "enabled": True
                }
            },
            "piston": {
                "area_scale": 1.0,
                "crown_temperature_K": 520.0
            },
            "liner": {
                "area_scale": 1.0,
                "wall_temperature_K": 430.0
            },
            "head": {
                "area_scale": 1.0,
                "wall_temperature_K": 480.0
            }
        },
        {
            "name": "user_cylinder_2",
            "enabled": False,
            "crank_angle_offset_deg": 360.0,
            "actuation_source": "auto",
            "notes": "Secondary cylinder template",
            "connections": {
                "intake_name": "intake_manifold_2",
                "exhaust_name": "exhaust_manifold_2"
            },
            "runners": {
                "intake": {
                    "length_m": 0.25,
                    "diameter_m": 0.035,
                    "volume_m3": 0.00024,
                    "zeta_local": 1.2,
                    "friction_factor": 0.03,
                    "wall_temperature_K": 320.0,
                    "enabled": True
                },
                "exhaust": {
                    "length_m": 0.35,
                    "diameter_m": 0.03,
                    "volume_m3": 0.00025,
                    "zeta_local": 1.8,
                    "friction_factor": 0.04,
                    "wall_temperature_K": 650.0,
                    "enabled": True
                }
            },
            "piston": {
                "area_scale": 1.0,
                "crown_temperature_K": 520.0
            },
            "liner": {
                "area_scale": 1.0,
                "wall_temperature_K": 430.0
            },
            "head": {
                "area_scale": 1.0,
                "wall_temperature_K": 480.0
            }
        }
    ],
    "active_user_cylinder": "user_cylinder_1",
    "angle_reference": {
        "mode": "FIRE_TDC",
        "plot_theta_min_deg": -360.0,
        "plot_theta_max_deg": 360.0
    },
    "postprocess": {
        "slot_events": {
            "enabled": True,
            "area_threshold_m2": 1e-7,
            "per_group": True,
            "per_group_blowdown": True,
            "plot_groups": True
        },
        "group_contributions": {
            "enabled": True,
            "area_threshold_m2": 1e-7
        },
        "group_flow_model": {
            "enabled": True,
            "mode": "independent_nozzles_with_channel_losses"
        }
    }
}

def get_default_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)

def deep_merge(base: dict, update: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (update or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result

def normalize_config(config: dict | None) -> dict:
    return deep_merge(get_default_config(), config or {})
