from dataclasses import dataclass
from typing import Any

@dataclass
class RHSContext:
    cfg: Any
    engine: Any
    kin: Any
    gas: Any
    area_provider: Any
    submodels: list
    cylinder: Any = None               # active / primary cylinder for compatibility
    cylinders: list | None = None      # enabled cylinders for multi-cylinder RHS
    model_state: Any = None
    signals: dict = None

    def reset_signals(self):
        self.signals = {}
