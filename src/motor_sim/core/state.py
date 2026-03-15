from dataclasses import dataclass
from typing import Dict, List

@dataclass
class StateIndex:
    names: List[str]
    idx: Dict[str, int]

    @staticmethod
    def from_names(names: List[str]) -> "StateIndex":
        return StateIndex(names=names, idx={n: i for i, n in enumerate(names)})

    def i(self, name: str) -> int:
        return self.idx[name]
