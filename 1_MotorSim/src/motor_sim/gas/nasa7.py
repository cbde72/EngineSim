from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import math

R_UNIVERSAL = 8.31446261815324  # J/mol/K
ATM = 101325.0

_ATOMIC_WEIGHTS = {
    "H": 1.00784e-3,
    "C": 12.0107e-3,
    "O": 15.999e-3,
    "N": 14.0067e-3,
    "AR": 39.948e-3,
}


@dataclass(frozen=True)
class NASA7:
    name: str
    composition: Mapping[str, float]
    temperature_ranges: tuple[float, float, float]
    low: tuple[float, float, float, float, float, float, float]
    high: tuple[float, float, float, float, float, float, float]
    source: str = ""

    @property
    def molecular_weight_kg_per_mol(self) -> float:
        mw = 0.0
        for element, count in self.composition.items():
            key = element.upper()
            if key not in _ATOMIC_WEIGHTS:
                raise KeyError(f"Atomic weight for element '{element}' is not defined.")
            mw += _ATOMIC_WEIGHTS[key] * float(count)
        return mw

    @property
    def R_specific(self) -> float:
        return R_UNIVERSAL / self.molecular_weight_kg_per_mol

    def _coeffs(self, T: float) -> tuple[float, float, float, float, float, float, float]:
        return self.low if T <= self.temperature_ranges[1] else self.high

    def cp_R(self, T: float) -> float:
        a1, a2, a3, a4, a5, _, _ = self._coeffs(T)
        return a1 + a2*T + a3*T*T + a4*T**3 + a5*T**4

    def h_RT(self, T: float) -> float:
        a1, a2, a3, a4, a5, a6, _ = self._coeffs(T)
        return a1 + a2*T/2.0 + a3*T*T/3.0 + a4*T**3/4.0 + a5*T**4/5.0 + a6/T

    def s_R(self, T: float) -> float:
        a1, a2, a3, a4, a5, _, a7 = self._coeffs(T)
        return a1 * math.log(T) + a2*T + a3*T*T/2.0 + a4*T**3/3.0 + a5*T**4/4.0 + a7

    def cp_molar(self, T: float) -> float:
        return R_UNIVERSAL * self.cp_R(T)

    def cv_molar(self, T: float) -> float:
        return self.cp_molar(T) - R_UNIVERSAL

    def h_molar(self, T: float) -> float:
        return R_UNIVERSAL * T * self.h_RT(T)

    def u_molar(self, T: float) -> float:
        return self.h_molar(T) - R_UNIVERSAL * T

    def s_molar(self, T: float, p: float = ATM) -> float:
        return R_UNIVERSAL * self.s_R(T) - R_UNIVERSAL * math.log(max(p, 1e-30) / ATM)

    def cp_mass(self, T: float) -> float:
        return self.cp_molar(T) / self.molecular_weight_kg_per_mol

    def cv_mass(self, T: float) -> float:
        return self.cv_molar(T) / self.molecular_weight_kg_per_mol

    def h_mass(self, T: float) -> float:
        return self.h_molar(T) / self.molecular_weight_kg_per_mol

    def u_mass(self, T: float) -> float:
        return self.u_molar(T) / self.molecular_weight_kg_per_mol

    def gamma(self, T: float) -> float:
        return self.cp_molar(T) / self.cv_molar(T)


@dataclass(frozen=True)
class IdealGasMixture:
    species: tuple[NASA7, ...]
    mole_fractions: tuple[float, ...]

    @property
    def normalized_mole_fractions(self) -> tuple[float, ...]:
        s = sum(self.mole_fractions)
        if s <= 0.0:
            raise ValueError("Mixture mole fractions must sum to a positive value.")
        return tuple(x / s for x in self.mole_fractions)

    @property
    def molecular_weight_kg_per_mol(self) -> float:
        x = self.normalized_mole_fractions
        return sum(xi * sp.molecular_weight_kg_per_mol for sp, xi in zip(self.species, x))

    @property
    def R_specific(self) -> float:
        return R_UNIVERSAL / self.molecular_weight_kg_per_mol

    def cp_molar(self, T: float) -> float:
        x = self.normalized_mole_fractions
        return sum(xi * sp.cp_molar(T) for sp, xi in zip(self.species, x))

    def cv_molar(self, T: float) -> float:
        return self.cp_molar(T) - R_UNIVERSAL

    def cp_mass(self, T: float) -> float:
        return self.cp_molar(T) / self.molecular_weight_kg_per_mol

    def cv_mass(self, T: float) -> float:
        return self.cv_molar(T) / self.molecular_weight_kg_per_mol

    def gamma(self, T: float) -> float:
        return self.cp_molar(T) / self.cv_molar(T)

    def h_molar(self, T: float) -> float:
        x = self.normalized_mole_fractions
        return sum(xi * sp.h_molar(T) for sp, xi in zip(self.species, x))

    def h_mass(self, T: float) -> float:
        return self.h_molar(T) / self.molecular_weight_kg_per_mol


def ideal_gas_pressure(rho: float, T: float, R_specific: float) -> float:
    return rho * R_specific * T
