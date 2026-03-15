from dataclasses import dataclass

@dataclass(frozen=True)
class IdealGas:
    R: float
    cp: float

    @property
    def cv(self):
        return self.cp - self.R

    @property
    def gamma(self):
        return self.cp / self.cv

    def p_from_mTV(self, m, T, V):
        return (m * self.R * T) / max(V, 1e-12)
