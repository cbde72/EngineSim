from __future__ import annotations

from dataclasses import replace

from motor_sim.config import GasCfg
from motor_sim.core.builder import ModelBuilder
from motor_sim.gas.nasa7_library import complete_combustion_products
from motor_sim.gas.thermo import build_thermo_from_config


def test_complete_combustion_products_lean_methanol_contains_expected_species():
    products = complete_combustion_products('methanol', lambda_air=1.2)
    assert products['CO2'] > 0.0
    assert products['H2O'] > 0.0
    assert products['O2'] > 0.0
    assert products['N2'] > 0.0
    assert 'CH3OH' not in products


def test_complete_combustion_products_rich_ethanol_keeps_unburned_fuel():
    products = complete_combustion_products('ethanol', lambda_air=0.8)
    assert products['CO2'] > 0.0
    assert products['H2O'] > 0.0
    assert products['C2H5OH'] > 0.0
    assert 'O2' not in products


def test_build_combustion_products_thermo_uses_lambda_from_combustion_cfg():
    gas = build_thermo_from_config(
        GasCfg(
            R_J_per_kgK=287.0,
            cp_J_per_kgK=1005.0,
            thermo_mode='nasa7_mixture',
            mixture_preset='combustion_products',
            combustion_products_fuel_name='hydrogen',
            combustion_products_lambda=1.0,
            combustion_products_lambda_source='combustion',
        ),
        combustion_cfg={'lambda': 2.0},
    )
    assert gas.R > 300.0
    assert gas.cp_mass(1200.0) > gas.cv_mass(1200.0)


def test_builder_accepts_combustion_products_mixture_mode(cfg):
    cfg2 = replace(
        cfg,
        gas=replace(
            cfg.gas,
            thermo_mode='nasa7_mixture',
            mixture_preset='combustion_products',
            combustion_products_fuel_name='methanol',
            combustion_products_lambda_source='combustion',
        ),
    )
    S, ctx, model, _t_span, y0 = ModelBuilder(cfg2).build()
    dy = model.rhs(0.0, y0.copy())
    assert dy.shape == y0.shape
    assert len(S.names) == y0.size
    assert ctx.gas.gamma_at(300.0) > 1.0
