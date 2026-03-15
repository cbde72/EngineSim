from __future__ import annotations

import math
from dataclasses import replace

from motor_sim.core.builder import ModelBuilder


def test_engine_derived_geometry_properties_are_consistent(cfg):
    S, ctx, model, t_span, y0 = ModelBuilder(cfg).build()
    engine = ctx.engine

    expected_area = math.pi / 4.0 * engine.bore_m ** 2
    expected_disp = expected_area * engine.stroke_m
    expected_clearance = expected_disp / (engine.compression_ratio - 1.0)

    assert math.isclose(engine.piston_area_m2, expected_area, rel_tol=1e-12)
    assert math.isclose(engine.displacement_m3, expected_disp, rel_tol=1e-12)
    assert math.isclose(engine.clearance_volume_m3, expected_clearance, rel_tol=1e-12)
    assert engine.total_displacement_m3 >= engine.displacement_m3


def test_state_layout_is_unique_and_complete_for_enabled_cylinders(cfg):
    S, ctx, model, t_span, y0 = ModelBuilder(cfg).build()

    assert len(S.names) == len(set(S.names)), 'State names must be unique.'
    assert S.names[:5] == [
        'theta',
        'm_int_plenum',
        'T_int_plenum',
        'm_ex_plenum',
        'T_ex_plenum',
    ]

    for cyl in ctx.cylinders:
        expected = [
            f'm_rin__{cyl.name}',
            f'T_rin__{cyl.name}',
            f'm_rex__{cyl.name}',
            f'T_rex__{cyl.name}',
            f'm__{cyl.name}',
            f'T__{cyl.name}',
        ]
        for name in expected:
            assert name in S.idx
            assert 0 <= S.i(name) < len(S.names)


def test_active_cylinder_falls_back_to_first_enabled_when_name_is_invalid(cfg):
    cfg2 = replace(cfg, active_user_cylinder='__does_not_exist__')
    S, ctx, model, t_span, y0 = ModelBuilder(cfg2).build()

    assert len(ctx.cylinders) >= 1
    assert ctx.cylinder.name == ctx.cylinders[0].name
