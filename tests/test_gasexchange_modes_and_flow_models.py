from __future__ import annotations

from dataclasses import replace

import numpy as np

from motor_sim.core.builder import ModelBuilder



def _build_with_mode(cfg, mode: str, flow_model: str | None = None):
    ge = cfg.gasexchange
    kwargs = {"mode": mode, "enabled": True}
    if flow_model is not None:
        kwargs["flow_model"] = flow_model
    ge2 = replace(ge, **kwargs)
    cfg2 = replace(cfg, gasexchange=ge2)
    return ModelBuilder(cfg2).build()



def test_builder_and_rhs_work_for_all_supported_gasexchange_modes(cfg):
    for mode in ["valves", "ports", "slots"]:
        S, ctx, model, t_span, y0 = _build_with_mode(cfg, mode)
        dy = model.rhs(t_span[0], y0.copy())

        assert dy.shape == y0.shape
        assert np.all(np.isfinite(dy)), f"Non-finite rhs output for gasexchange.mode={mode}"
        assert len(ctx.cylinders) >= 1
        assert f"{ctx.cylinders[0].name}__p_cyl_pa" in ctx.signals



def test_rhs_is_finite_for_both_supported_flow_models(cfg):
    for flow_model in ["nozzle_choked", "simple_orifice"]:
        S, ctx, model, t_span, y0 = _build_with_mode(cfg, cfg.gasexchange.mode, flow_model=flow_model)
        dy = model.rhs(t_span[0], y0.copy())

        assert dy.shape == y0.shape
        assert np.all(np.isfinite(dy)), f"Non-finite rhs output for flow_model={flow_model}"
        assert np.isfinite(float(ctx.signals["mdot_feed_int_kg_s"]))
        assert np.isfinite(float(ctx.signals["mdot_discharge_ex_kg_s"]))
