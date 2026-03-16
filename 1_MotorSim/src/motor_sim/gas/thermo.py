from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .idealgas import IdealGas
from .nasa7 import NASA7, IdealGasMixture
from .nasa7_library import get_species, dry_air, combustion_products_mixture


class ThermoModel:
    @property
    def R(self) -> float:
        raise NotImplementedError

    def R_at(self, T: float) -> float:
        return float(self.R)

    @property
    def cp(self) -> float:
        return self.cp_mass(300.0)

    @property
    def cv(self) -> float:
        return self.cv_mass(300.0)

    @property
    def gamma(self) -> float:
        return self.gamma_at(300.0)

    def cp_mass(self, T: float) -> float:
        raise NotImplementedError

    def cv_mass(self, T: float) -> float:
        raise NotImplementedError

    def gamma_at(self, T: float) -> float:
        return self.cp_mass(T) / max(self.cv_mass(T), 1e-12)

    def h_mass(self, T: float) -> float:
        raise NotImplementedError

    def u_mass(self, T: float) -> float:
        raise NotImplementedError

    def p_from_mTV(self, m: float, T: float, V: float) -> float:
        return (float(m) * self.R * float(T)) / max(float(V), 1e-12)

    def temperature_from_u_mass(self, u_mass_target: float, T_low: float = 150.0, T_high: float = 5000.0) -> float:
        low = float(T_low)
        high = float(T_high)
        u_low = self.u_mass(low)
        u_high = self.u_mass(high)
        target = float(u_mass_target)
        if target <= u_low:
            return low
        if target >= u_high:
            return high
        for _ in range(80):
            mid = 0.5 * (low + high)
            u_mid = self.u_mass(mid)
            if u_mid < target:
                low = mid
            else:
                high = mid
        return 0.5 * (low + high)

    def temperature_from_mass_energy(self, mass: float, energy: float, min_mass_kg: float = 1e-12) -> float:
        m = max(float(mass), float(min_mass_kg))
        return self.temperature_from_u_mass(float(energy) / m)

    def internal_energy_from_mass_temp(self, mass: float, temperature: float) -> float:
        return float(mass) * self.u_mass(float(temperature))


@dataclass(frozen=True)
class ConstCpThermo(ThermoModel):
    model: IdealGas

    @property
    def R(self) -> float:
        return float(self.model.R)

    def cp_mass(self, T: float) -> float:
        return float(self.model.cp)

    def cv_mass(self, T: float) -> float:
        return float(self.model.cv)

    def h_mass(self, T: float) -> float:
        return float(self.model.cp) * float(T)

    def u_mass(self, T: float) -> float:
        return float(self.model.cv) * float(T)

    def temperature_from_u_mass(self, u_mass_target: float, T_low: float = 150.0, T_high: float = 5000.0) -> float:
        return float(u_mass_target) / max(self.model.cv, 1e-12)


@dataclass(frozen=True)
class NASA7SpeciesThermo(ThermoModel):
    species: NASA7

    @property
    def R(self) -> float:
        return float(self.species.R_specific)

    def cp_mass(self, T: float) -> float:
        return float(self.species.cp_mass(float(T)))

    def cv_mass(self, T: float) -> float:
        return float(self.species.cv_mass(float(T)))

    def h_mass(self, T: float) -> float:
        return float(self.species.h_mass(float(T)))

    def u_mass(self, T: float) -> float:
        return float(self.species.u_mass(float(T)))

    def gamma_at(self, T: float) -> float:
        return float(self.species.gamma(float(T)))


@dataclass(frozen=True)
class NASA7MixtureThermo(ThermoModel):
    mixture: IdealGasMixture

    @property
    def R(self) -> float:
        return float(self.mixture.R_specific)

    def R_at(self, T: float) -> float:
        return float(self.mixture.R_specific)

    def cp_mass(self, T: float) -> float:
        return float(self.mixture.cp_mass(float(T)))

    def cv_mass(self, T: float) -> float:
        return float(self.mixture.cv_mass(float(T)))

    def h_mass(self, T: float) -> float:
        return float(self.mixture.h_mass(float(T)))

    def u_mass(self, T: float) -> float:
        return self.h_mass(T) - self.R * float(T)

    def gamma_at(self, T: float) -> float:
        return float(self.mixture.gamma(float(T)))



@dataclass(frozen=True)
class TemperatureCoupledCombustionProductsThermo(ThermoModel):
    fuel_name: str
    lambda_air: float
    rich_mode: str = "simple"
    equilibrium_strength: float = 0.35
    equilibrium_enabled: bool = True
    equilibrium_temperature_min_K: float = 1200.0
    equilibrium_temperature_max_K: float = 3000.0

    def _mixture_at(self, T: float) -> IdealGasMixture:
        T_eval = float(T)
        if not self.equilibrium_enabled:
            T_eval = 300.0
        T_eval = max(float(self.equilibrium_temperature_min_K), min(float(self.equilibrium_temperature_max_K), T_eval))
        return combustion_products_mixture(
            fuel_name=self.fuel_name,
            lambda_air=self.lambda_air,
            rich_mode=self.rich_mode,
            equilibrium_lite=self.equilibrium_enabled,
            equilibrium_temperature_K=T_eval,
            equilibrium_strength=self.equilibrium_strength,
        )

    @property
    def R(self) -> float:
        return self.R_at(300.0)

    def R_at(self, T: float) -> float:
        return float(self._mixture_at(T).R_specific)

    def cp_mass(self, T: float) -> float:
        return float(self._mixture_at(T).cp_mass(float(T)))

    def cv_mass(self, T: float) -> float:
        return float(self._mixture_at(T).cv_mass(float(T)))

    def h_mass(self, T: float) -> float:
        return float(self._mixture_at(T).h_mass(float(T)))

    def u_mass(self, T: float) -> float:
        mix = self._mixture_at(T)
        return float(mix.h_mass(float(T)) - mix.R_specific * float(T))

    def gamma_at(self, T: float) -> float:
        return float(self._mixture_at(T).gamma(float(T)))

    def p_from_mTV(self, m: float, T: float, V: float) -> float:
        return (float(m) * self.R_at(float(T)) * float(T)) / max(float(V), 1e-12)

def _resolve_products_lambda(gas_cfg, combustion_cfg=None) -> float:
    source = str(getattr(gas_cfg, 'combustion_products_lambda_source', 'combustion')).strip().lower()
    if source in {'gas', 'fixed', 'config'}:
        return float(getattr(gas_cfg, 'combustion_products_lambda', 1.0))
    if source in {'combustion', 'energy_models', 'auto'}:
        comb = combustion_cfg or {}
        if isinstance(comb, Mapping):
            return float(comb.get('lambda', getattr(gas_cfg, 'combustion_products_lambda', 1.0)))
        return float(getattr(gas_cfg, 'combustion_products_lambda', 1.0))
    raise ValueError(f"Unknown gas.combustion_products_lambda_source: {source}")


def build_thermo_from_config(gas_cfg, combustion_cfg=None) -> ThermoModel:
    mode = str(getattr(gas_cfg, 'thermo_mode', 'const')).strip().lower()
    if mode in {'const', 'constant', 'cp_const', 'ideal_const'}:
        return ConstCpThermo(IdealGas(R=float(gas_cfg.R_J_per_kgK), cp=float(gas_cfg.cp_J_per_kgK)))

    if mode in {'nasa7_species', 'species'}:
        species_name = str(getattr(gas_cfg, 'species_name', 'air')).strip()
        if species_name.lower() in {'air', 'dry_air', 'luft'}:
            return NASA7MixtureThermo(dry_air())
        species = get_species(species_name)
        return NASA7SpeciesThermo(species)

    if mode in {'nasa7_mixture', 'mixture'}:
        preset = str(getattr(gas_cfg, 'mixture_preset', '') or '').strip().lower()
        if preset in {'', 'custom'}:
            composition = dict(getattr(gas_cfg, 'mixture_mole_fractions', {}) or {})
            if not composition:
                composition = {'N2': 0.78084, 'O2': 0.20946, 'AR': 0.00934}
        elif preset in {'air', 'dry_air', 'luft'}:
            return NASA7MixtureThermo(dry_air())
        elif preset in {'combustion_products', 'products', 'burned_gas', 'combustion'}:
            fuel_name = str(getattr(gas_cfg, 'combustion_products_fuel_name', '') or getattr(gas_cfg, 'species_name', 'methanol')).strip()
            if fuel_name.lower() in {'air', 'dry_air', 'luft', ''}:
                fuel_name = 'methanol'
            lambda_air = _resolve_products_lambda(gas_cfg, combustion_cfg=combustion_cfg)
            rich_mode = str(getattr(gas_cfg, 'combustion_products_rich_mode', 'simple')).strip().lower()
            equilibrium_lite_enabled = bool(getattr(gas_cfg, 'combustion_products_equilibrium_lite_enabled', False))
            equilibrium_lite_temperature_K = float(getattr(gas_cfg, 'combustion_products_equilibrium_lite_temperature_K', 2200.0))
            equilibrium_lite_strength = float(getattr(gas_cfg, 'combustion_products_equilibrium_lite_strength', 0.35))
            equilibrium_lite_temperature_source = str(getattr(gas_cfg, 'combustion_products_equilibrium_lite_temperature_source', 'config')).strip().lower()
            equilibrium_lite_temperature_min_K = float(getattr(gas_cfg, 'combustion_products_equilibrium_lite_temperature_min_K', 1200.0))
            equilibrium_lite_temperature_max_K = float(getattr(gas_cfg, 'combustion_products_equilibrium_lite_temperature_max_K', 3000.0))
            if equilibrium_lite_enabled and equilibrium_lite_temperature_source in {'cylinder', 'state', 'dynamic', 'temperature_coupled'}:
                return TemperatureCoupledCombustionProductsThermo(
                    fuel_name=fuel_name,
                    lambda_air=lambda_air,
                    rich_mode=rich_mode,
                    equilibrium_strength=equilibrium_lite_strength,
                    equilibrium_enabled=True,
                    equilibrium_temperature_min_K=equilibrium_lite_temperature_min_K,
                    equilibrium_temperature_max_K=equilibrium_lite_temperature_max_K,
                )
            return NASA7MixtureThermo(combustion_products_mixture(
                fuel_name=fuel_name,
                lambda_air=lambda_air,
                rich_mode=rich_mode,
                equilibrium_lite=equilibrium_lite_enabled,
                equilibrium_temperature_K=equilibrium_lite_temperature_K,
                equilibrium_strength=equilibrium_lite_strength,
            ))
        else:
            raise ValueError(f'Unknown gas.mixture_preset: {preset}')

        species_objs = []
        mole_fracs = []
        for name, frac in composition.items():
            species_objs.append(get_species(str(name)))
            mole_fracs.append(float(frac))
        return NASA7MixtureThermo(IdealGasMixture(tuple(species_objs), tuple(mole_fracs)))

    raise ValueError(f'Unknown gas.thermo_mode: {mode}')
