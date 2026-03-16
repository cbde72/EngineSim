from __future__ import annotations

from dataclasses import replace

from motor_sim.config import GasCfg
from motor_sim.core.builder import ModelBuilder
from motor_sim.gas.thermo import build_thermo_from_config


def test_build_const_thermo_from_config():
    gas = build_thermo_from_config(GasCfg(R_J_per_kgK=287.0, cp_J_per_kgK=1005.0, thermo_mode='const'))
    assert abs(gas.R - 287.0) < 1e-12
    assert abs(gas.cp_mass(500.0) - 1005.0) < 1e-12
    assert gas.cv_mass(500.0) > 0.0


def test_build_nasa7_species_thermo_from_config():
    gas = build_thermo_from_config(GasCfg(R_J_per_kgK=287.0, cp_J_per_kgK=1005.0, thermo_mode='nasa7_species', species_name='methanol'))
    assert gas.R > 100.0
    assert gas.cp_mass(1200.0) > gas.cv_mass(1200.0)
    assert gas.u_mass(1200.0) > gas.u_mass(400.0)


def test_build_nasa7_mixture_thermo_from_config():
    gas = build_thermo_from_config(
        GasCfg(
            R_J_per_kgK=287.0,
            cp_J_per_kgK=1005.0,
            thermo_mode='nasa7_mixture',
            mixture_mole_fractions={'N2': 0.79, 'O2': 0.21},
        )
    )
    assert 280.0 < gas.R < 300.0
    assert gas.gamma_at(300.0) > gas.gamma_at(2500.0)


def test_builder_accepts_nasa7_species_mode(cfg):
    cfg2 = replace(cfg, gas=replace(cfg.gas, thermo_mode='nasa7_species', species_name='air'))
    S, ctx, model, _t_span, y0 = ModelBuilder(cfg2).build()
    dy = model.rhs(0.0, y0.copy())
    assert len(S.names) == y0.size
    assert dy.shape == y0.shape
    assert ctx.gas.cp_mass(1200.0) > ctx.gas.cv_mass(1200.0)


def test_builder_accepts_nasa7_mixture_mode(cfg):
    cfg2 = replace(
        cfg,
        gas=replace(
            cfg.gas,
            thermo_mode='nasa7_mixture',
            mixture_preset='custom',
            mixture_mole_fractions={'N2': 0.78084, 'O2': 0.20946, 'AR': 0.00934},
        ),
    )
    _S, ctx, model, _t_span, y0 = ModelBuilder(cfg2).build()
    dy = model.rhs(0.0, y0.copy())
    assert dy.shape == y0.shape
    assert abs(ctx.gas.R - 287.0) < 5.0
