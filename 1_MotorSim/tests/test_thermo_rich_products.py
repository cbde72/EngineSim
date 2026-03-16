from __future__ import annotations

import pytest

from dataclasses import replace

from motor_sim.config import GasCfg
from motor_sim.core.builder import ModelBuilder
from motor_sim.gas.nasa7_library import complete_combustion_products, get_species
from motor_sim.gas.thermo import build_thermo_from_config


def _element_totals(mixture: dict[str, float]) -> dict[str, float]:
    totals = {"C": 0.0, "H": 0.0, "O": 0.0, "N": 0.0, "AR": 0.0}
    for name, amount in mixture.items():
        sp = get_species(name)
        for elem, count in sp.composition.items():
            key = elem.upper()
            if key in totals:
                totals[key] += float(count) * float(amount)
    return totals


def _reactant_atoms(fuel_name: str, lambda_air: float) -> dict[str, float]:
    fuel = get_species(fuel_name)
    lam = float(lambda_air)
    from motor_sim.gas.nasa7_library import dry_air, stoich_o2_moles_per_mole_fuel
    air = dry_air()
    x_o2, x_n2, x_ar = air.normalized_mole_fractions
    o2_in = lam * stoich_o2_moles_per_mole_fuel(fuel)
    return {
        "C": float(fuel.composition.get("C", 0.0)),
        "H": float(fuel.composition.get("H", 0.0)),
        "O": float(fuel.composition.get("O", 0.0)) + 2.0 * o2_in,
        "N": 2.0 * o2_in * x_n2 / x_o2,
        "AR": 1.0 * o2_in * x_ar / x_o2,
    }


def test_extended_rich_products_ethanol_contains_co_and_no_unburned_fuel_for_moderately_rich_case():
    products = complete_combustion_products('ethanol', lambda_air=0.8, rich_mode='extended')
    assert products['CO2'] > 0.0
    assert products['CO'] > 0.0
    assert products['H2O'] > 0.0
    assert 'C2H5OH' not in products
    assert 'O2' not in products


def test_extended_rich_products_very_rich_diesel_contains_co_h2_and_unburned_fuel():
    products = complete_combustion_products('diesel', lambda_air=0.2, rich_mode='extended')
    assert products['CO'] > 0.0
    assert products['H2'] > 0.0
    assert products['NC12H26'] > 0.0
    assert 'O2' not in products


def test_extended_rich_products_preserve_element_balance_for_ethanol():
    lam = 0.55
    products = complete_combustion_products('ethanol', lambda_air=lam, rich_mode='extended')
    prod = _element_totals(products)
    reac = _reactant_atoms('ethanol', lam)
    for key in reac:
        assert prod[key] == pytest.approx(reac[key], rel=1e-10, abs=1e-10)


def test_simple_and_extended_modes_differ_for_rich_ethanol():
    simple = complete_combustion_products('ethanol', lambda_air=0.8, rich_mode='simple')
    extended = complete_combustion_products('ethanol', lambda_air=0.8, rich_mode='extended')
    assert 'C2H5OH' in simple
    assert 'CO' in extended


def test_build_combustion_products_extended_rich_mode_from_config():
    gas = build_thermo_from_config(
        GasCfg(
            R_J_per_kgK=287.0,
            cp_J_per_kgK=1005.0,
            thermo_mode='nasa7_mixture',
            mixture_preset='combustion_products',
            combustion_products_fuel_name='ethanol',
            combustion_products_lambda=0.8,
            combustion_products_lambda_source='config',
            combustion_products_rich_mode='extended',
        )
    )
    assert gas.R > 0.0
    assert gas.gamma_at(1000.0) > 1.0


def test_builder_accepts_extended_rich_products_mode(cfg):
    cfg2 = replace(
        cfg,
        gas=replace(
            cfg.gas,
            thermo_mode='nasa7_mixture',
            mixture_preset='combustion_products',
            combustion_products_fuel_name='ethanol',
            combustion_products_lambda=0.75,
            combustion_products_lambda_source='config',
            combustion_products_rich_mode='extended',
        ),
    )
    S, ctx, model, _t_span, y0 = ModelBuilder(cfg2).build()
    dy = model.rhs(0.0, y0.copy())
    assert dy.shape == y0.shape
    assert ctx.gas.gamma_at(900.0) > 1.0
