from __future__ import annotations


def test_load_config_has_expected_core_sections(cfg):
    assert cfg.engine.cycle_type in {"2T", "4T"}
    assert cfg.gas.R_J_per_kgK > 0.0
    assert cfg.gas.cp_J_per_kgK > cfg.gas.R_J_per_kgK
    assert len(cfg.user_cylinders) >= 1
    assert cfg.active_user_cylinder


def test_builder_creates_consistent_state_layout(built_model):
    S = built_model["S"]
    ctx = built_model["ctx"]
    y0 = built_model["y0"]

    n_cyl = len(ctx.cylinders)
    expected_n_states = 5 + 6 * n_cyl

    assert len(S.names) == expected_n_states
    assert y0.shape == (expected_n_states,)
    assert S.names[:5] == [
        "theta",
        "m_int_plenum",
        "T_int_plenum",
        "m_ex_plenum",
        "T_ex_plenum",
    ]

    for cyl in ctx.cylinders:
        for name in (
            f"m_rin__{cyl.name}",
            f"T_rin__{cyl.name}",
            f"m_rex__{cyl.name}",
            f"T_rex__{cyl.name}",
            f"m__{cyl.name}",
            f"T__{cyl.name}",
        ):
            assert name in S.idx


def test_builder_returns_active_cylinder_present_in_cylinders(built_model):
    ctx = built_model["ctx"]
    cyl_names = [c.name for c in ctx.cylinders]
    assert ctx.cylinder.name in cyl_names
