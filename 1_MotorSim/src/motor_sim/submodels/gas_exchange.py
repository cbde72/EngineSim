from dataclasses import dataclass
from motor_sim.flow.nozzle_choked import mdot_nozzle_signed

@dataclass(frozen=True)
class Manifolds:
    p_int: float; T_int: float; p_ex: float; T_ex: float

class GasExchange:
    def __init__(self, manifolds: Manifolds, flow_model: str):
        self.man = manifolds
        self.flow_model = flow_model

    def contribute(self, t, y, ctx, aux, dy):
        raise NotImplementedError(
            "Legacy GasExchange is deprecated in the signed-flow branch. "
            "Use core.model.Model with port_flow.signed_port_mdot for consistent intake reversion and exhaust blowback handling."
        )
