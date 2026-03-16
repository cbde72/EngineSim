from __future__ import annotations

from typing import Dict, Mapping

from .nasa7 import NASA7, IdealGasMixture

RAW_DATABASE: Dict[str, dict] = {
  "AR": {
    "composition": {
      "Ar": 1
    },
    "data": [
      [
        2.5,
        0.0,
        0.0,
        0.0,
        0.0,
        -745.375,
        4.366
      ],
      [
        2.5,
        0.0,
        0.0,
        0.0,
        0.0,
        -745.375,
        4.366
      ]
    ],
    "name": "AR",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      300.0,
      1000.0,
      5000.0
    ]
  },
  "C2H5OH": {
    "composition": {
      "C": 2,
      "H": 6,
      "O": 1
    },
    "data": [
      [
        0.215805861,
        0.0295228396,
        -1.68271048e-05,
        4.49484797e-09,
        -4.02451543e-13,
        -29485.1823,
        24.5725052
      ],
      [
        8.14483865,
        0.0128314052,
        -4.29052743e-06,
        6.55971721e-10,
        -3.76506611e-14,
        -32400.5526,
        -18.6241126
      ]
    ],
    "name": "C2H5OH",
    "source": "MechanismsForCFD Z74 ethanol-air mechanism",
    "temperature_ranges": [
      300.0,
      1402.0,
      5000.0
    ]
  },
  "CH3OH": {
    "composition": {
      "C": 1,
      "H": 4,
      "O": 1
    },
    "data": [
      [
        2.660115,
        0.007341508,
        7.170051e-06,
        -8.793194e-09,
        2.39057e-12,
        -25353.48,
        11.23263
      ],
      [
        4.029061,
        0.009376593,
        -3.050254e-06,
        4.358793e-10,
        -2.224723e-14,
        -26157.91,
        2.378196
      ]
    ],
    "name": "CH3OH",
    "source": "Cantera nDodecane_Reitz.yaml",
    "temperature_ranges": [
      300.0,
      1000.0,
      5000.0
    ]
  },
  "CO": {
    "composition": {
      "C": 1,
      "O": 1
    },
    "data": [
      [
        3.57953347,
        -0.00061035368,
        1.01681433e-06,
        9.07005884e-10,
        -9.04424499e-13,
        -14344.086,
        3.50840928
      ],
      [
        2.71518561,
        0.00206252743,
        -9.98825771e-07,
        2.30053008e-10,
        -2.03647716e-14,
        -14151.8724,
        7.81868772
      ]
    ],
    "name": "CO",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "CO2": {
    "composition": {
      "C": 1,
      "O": 2
    },
    "data": [
      [
        2.35677352,
        0.00898459677,
        -7.12356269e-06,
        2.45919022e-09,
        -1.43699548e-13,
        -48371.9697,
        9.90105222
      ],
      [
        3.85746029,
        0.00441437026,
        -2.21481404e-06,
        5.23490188e-10,
        -4.72084164e-14,
        -48759.166,
        2.27163806
      ]
    ],
    "name": "CO2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "H": {
    "composition": {
      "H": 1
    },
    "data": [
      [
        2.5,
        7.05332819e-13,
        -1.99591964e-15,
        2.30081632e-18,
        -9.27732332e-22,
        25473.6599,
        -0.446682853
      ],
      [
        2.50000001,
        -2.30842973e-11,
        1.61561948e-14,
        -4.73515235e-18,
        4.98197357e-22,
        25473.6599,
        -0.446682914
      ]
    ],
    "name": "H",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "H2": {
    "composition": {
      "H": 2
    },
    "data": [
      [
        2.34433112,
        0.00798052075,
        -1.9478151e-05,
        2.01572094e-08,
        -7.37611761e-12,
        -917.935173,
        0.683010238
      ],
      [
        3.3372792,
        -4.94024731e-05,
        4.99456778e-07,
        -1.79566394e-10,
        2.00255376e-14,
        -950.158922,
        -3.20502331
      ]
    ],
    "name": "H2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "H2O": {
    "composition": {
      "H": 2,
      "O": 1
    },
    "data": [
      [
        4.19864056,
        -0.0020364341,
        6.52040211e-06,
        -5.48797062e-09,
        1.77197817e-12,
        -30293.7267,
        -0.849032208
      ],
      [
        3.03399249,
        0.00217691804,
        -1.64072518e-07,
        -9.7041987e-11,
        1.68200992e-14,
        -30004.2971,
        4.9667701
      ]
    ],
    "name": "H2O",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "H2O2": {
    "composition": {
      "H": 2,
      "O": 2
    },
    "data": [
      [
        4.27611269,
        -0.000542822417,
        1.67335701e-05,
        -2.15770813e-08,
        8.62454363e-12,
        -17702.5821,
        3.43505074
      ],
      [
        4.16500285,
        0.00490831694,
        -1.90139225e-06,
        3.71185986e-10,
        -2.87908305e-14,
        -17861.7877,
        2.91615662
      ]
    ],
    "name": "H2O2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "HO2": {
    "composition": {
      "H": 1,
      "O": 2
    },
    "data": [
      [
        4.30179801,
        -0.00474912051,
        2.11582891e-05,
        -2.42763894e-08,
        9.29225124e-12,
        294.80804,
        3.71666245
      ],
      [
        4.0172109,
        0.00223982013,
        -6.3365815e-07,
        1.1424637e-10,
        -1.07908535e-14,
        111.856713,
        3.78510215
      ]
    ],
    "name": "HO2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "IC8H18": {
    "composition": {
      "C": 8,
      "H": 18
    },
    "data": [
      [
        -5.96912082,
        0.12087217,
        -9.61538218e-05,
        4.1348929e-08,
        -7.18982937e-12,
        -30267.5122,
        52.7954202
      ],
      [
        20.6155885,
        0.0443694094,
        -1.35968858e-05,
        1.75327621e-09,
        -6.83090867e-14,
        -37658.0614,
        -84.2148794
      ]
    ],
    "name": "IC8H18",
    "source": "MechanismsForCFD Z153 C8-C12 mechanism",
    "temperature_ranges": [
      300.0,
      1390.0,
      3500.0
    ]
  },
  "N2": {
    "composition": {
      "N": 2
    },
    "data": [
      [
        3.298677,
        0.0014082404,
        -3.963222e-06,
        5.641515e-09,
        -2.444854e-12,
        -1020.8999,
        3.950372
      ],
      [
        2.92664,
        0.0014879768,
        -5.68476e-07,
        1.0097038e-10,
        -6.753351e-15,
        -922.7977,
        5.980528
      ]
    ],
    "name": "N2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      300.0,
      1000.0,
      5000.0
    ]
  },
  "NC12H26": {
    "composition": {
      "C": 12,
      "H": 26
    },
    "data": [
      [
        -2.62181594,
        0.147237711,
        -9.43970271e-05,
        3.07441268e-08,
        -4.0360223e-12,
        -40065.4253,
        50.0994626
      ],
      [
        38.5095037,
        0.0563550048,
        -1.914932e-05,
        2.96024862e-09,
        -1.7124415e-13,
        -54884.3465,
        -172.670922
      ]
    ],
    "name": "NC12H26",
    "source": "Cantera nDodecane_Reitz.yaml (c12h26)",
    "temperature_ranges": [
      300.0,
      1391.0,
      5000.0
    ]
  },
  "NO": {
    "composition": {
      "N": 1,
      "O": 1
    },
    "data": [
      [
        4.2184763,
        -0.004638976,
        1.1041022e-05,
        -9.3361354e-09,
        2.803577e-12,
        9844.623,
        2.2808464
      ],
      [
        3.2606056,
        0.0011911043,
        -4.2917048e-07,
        6.9457669e-11,
        -4.0336099e-15,
        9920.9746,
        6.3693027
      ]
    ],
    "name": "NO",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      6000.0
    ]
  },
  "NO2": {
    "composition": {
      "N": 1,
      "O": 2
    },
    "data": [
      [
        3.9440312,
        -0.001585429,
        1.6657812e-05,
        -2.0475426e-08,
        7.8350564e-12,
        2896.6179,
        6.3119917
      ],
      [
        4.8847542,
        0.0021723956,
        -8.2806906e-07,
        1.574751e-10,
        -1.0510895e-14,
        2316.4983,
        -0.11741695
      ]
    ],
    "name": "NO2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      6000.0
    ]
  },
  "O": {
    "composition": {
      "O": 1
    },
    "data": [
      [
        3.1682671,
        -0.00327931884,
        6.64306396e-06,
        -6.12806624e-09,
        2.11265971e-12,
        29122.2592,
        2.05193346
      ],
      [
        2.56942078,
        -8.59741137e-05,
        4.19484589e-08,
        -1.00177799e-11,
        1.22833691e-15,
        29217.5791,
        4.78433864
      ]
    ],
    "name": "O",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "O2": {
    "composition": {
      "O": 2
    },
    "data": [
      [
        3.78245636,
        -0.00299673416,
        9.84730201e-06,
        -9.68129509e-09,
        3.24372837e-12,
        -1063.94356,
        3.65767573
      ],
      [
        3.28253784,
        0.00148308754,
        -7.57966669e-07,
        2.09470555e-10,
        -2.16717794e-14,
        -1088.45772,
        5.45323129
      ]
    ],
    "name": "O2",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  },
  "OH": {
    "composition": {
      "H": 1,
      "O": 1
    },
    "data": [
      [
        3.99201543,
        -0.00240131752,
        4.61793841e-06,
        -3.88113333e-09,
        1.3641147e-12,
        3615.08056,
        -0.103925458
      ],
      [
        3.09288767,
        0.000548429716,
        1.26505228e-07,
        -8.79461556e-11,
        1.17412376e-14,
        3858.657,
        4.4766961
      ]
    ],
    "name": "OH",
    "source": "Cantera gri30.yaml",
    "temperature_ranges": [
      200.0,
      1000.0,
      3500.0
    ]
  }
}


def _to_species(entry: dict) -> NASA7:
    data = entry["data"]
    return NASA7(
        name=entry["name"],
        composition=entry["composition"],
        temperature_ranges=tuple(float(v) for v in entry["temperature_ranges"]),
        low=tuple(float(v) for v in data[0]),
        high=tuple(float(v) for v in data[1]),
        source=entry.get("source", ""),
    )


SPECIES_DB: Dict[str, NASA7] = {name: _to_species(entry) for name, entry in RAW_DATABASE.items()}

ALIASES: Dict[str, str] = {
    "methanol": "CH3OH",
    "ch3oh": "CH3OH",
    "ethanol": "C2H5OH",
    "c2h5oh": "C2H5OH",
    "gasoline": "IC8H18",
    "benzin": "IC8H18",
    "isooctane": "IC8H18",
    "iso-octane": "IC8H18",
    "ic8h18": "IC8H18",
    "diesel": "NC12H26",
    "n-dodecane": "NC12H26",
    "ndodecane": "NC12H26",
    "nc12h26": "NC12H26",
    "hydrogen": "H2",
    "wasserstoff": "H2",
    "h2": "H2",
}

COMBUSTION_PRODUCT_NAMES = (
    "CO2", "H2O", "CO", "H2", "O2", "N2", "AR", "OH", "O", "H", "HO2", "H2O2", "NO", "NO2"
)


def get_species(name: str) -> NASA7:
    key = name.strip()
    upper = ALIASES.get(key.lower(), key.upper())
    if upper not in SPECIES_DB:
        raise KeyError(f"Unknown NASA species '{name}'. Available keys: {sorted(SPECIES_DB)}")
    return SPECIES_DB[upper]


def dry_air(o2: float = 0.2095, n2: float = 0.7808, ar: float = 0.0093) -> IdealGasMixture:
    return IdealGasMixture(
        species=(SPECIES_DB["O2"], SPECIES_DB["N2"], SPECIES_DB["AR"]),
        mole_fractions=(o2, n2, ar),
    )


def combustion_products_species() -> dict[str, NASA7]:
    return {name: SPECIES_DB[name] for name in COMBUSTION_PRODUCT_NAMES}


def fuel_species() -> dict[str, NASA7]:
    return {
        "methanol": SPECIES_DB["CH3OH"],
        "ethanol": SPECIES_DB["C2H5OH"],
        "gasoline_surrogate": SPECIES_DB["IC8H18"],
        "diesel_surrogate": SPECIES_DB["NC12H26"],
        "hydrogen": SPECIES_DB["H2"],
    }


def make_mixture(mole_fractions: Mapping[str, float]) -> IdealGasMixture:
    species = []
    fractions = []
    for name, value in mole_fractions.items():
        if value == 0.0:
            continue
        species.append(get_species(name))
        fractions.append(float(value))
    return IdealGasMixture(species=tuple(species), mole_fractions=tuple(fractions))


def stoich_o2_moles_per_mole_fuel(fuel: NASA7) -> float:
    c = float(fuel.composition.get("C", 0.0))
    h = float(fuel.composition.get("H", 0.0))
    o = float(fuel.composition.get("O", 0.0))
    return c + h / 4.0 - o / 2.0


def _air_dilution_moles(o2_in: float) -> tuple[float, float]:
    air = dry_air()
    x_o2, x_n2, x_ar = air.normalized_mole_fractions
    n2 = o2_in * x_n2 / x_o2
    ar = o2_in * x_ar / x_o2
    return n2, ar


def _complete_or_lean_products(fuel: NASA7, o2_in: float) -> dict[str, float]:
    o2_st = stoich_o2_moles_per_mole_fuel(fuel)
    c = float(fuel.composition.get("C", 0.0))
    h = float(fuel.composition.get("H", 0.0))
    n2, ar = _air_dilution_moles(o2_in)
    products = {
        "CO2": c,
        "H2O": h / 2.0,
        "O2": max(o2_in - o2_st, 0.0),
        "N2": n2,
        "AR": ar,
    }
    return {name: value for name, value in products.items() if value > 0.0}


def _simple_rich_products(fuel: NASA7, o2_in: float, lambda_air: float) -> dict[str, float]:
    c = float(fuel.composition.get("C", 0.0))
    h = float(fuel.composition.get("H", 0.0))
    n2, ar = _air_dilution_moles(o2_in)
    burned = max(min(float(lambda_air), 1.0), 0.0)
    unburned = max(1.0 - burned, 0.0)
    products = {
        "CO2": burned * c,
        "H2O": burned * h / 2.0,
        fuel.name: unburned,
        "N2": n2,
        "AR": ar,
    }
    return {name: value for name, value in products.items() if value > 0.0}


def _extended_rich_products(fuel: NASA7, o2_in: float) -> dict[str, float]:
    """Return a robust atom-balanced rich product set for 1 mol fuel.

    The closure is intentionally simple and solver-friendly. It uses three staged regimes:
    1) enough O for H2O plus mixed CO2/CO,
    2) enough O for CO plus mixed H2O/H2,
    3) otherwise partial conversion to CO/H2 with residual unburned fuel.

    This is not a chemical-equilibrium model.
    """
    c = float(fuel.composition.get("C", 0.0))
    h = float(fuel.composition.get("H", 0.0))
    z = float(fuel.composition.get("O", 0.0))

    n2, ar = _air_dilution_moles(o2_in)
    o_total = z + 2.0 * o2_in
    eps = 1e-12

    o_need_full = 2.0 * c + 0.5 * h
    o_need_co_h2o = c + 0.5 * h
    o_need_co_h2 = c

    products: dict[str, float] = {"N2": n2, "AR": ar}

    if o_total >= o_need_full - eps:
        products.update(_complete_or_lean_products(fuel, o2_in))
        return {name: value for name, value in products.items() if value > 0.0}

    if o_total >= o_need_co_h2o - eps:
        h2o = 0.5 * h
        o_for_carbon = max(o_total - h2o, 0.0)
        co2 = max(o_for_carbon - c, 0.0)
        co = max(2.0 * c - o_for_carbon, 0.0)
        products.update({
            "CO2": co2,
            "CO": co,
            "H2O": h2o,
        })
        return {name: value for name, value in products.items() if value > 0.0}

    if o_total >= o_need_co_h2 - eps:
        co = c
        o_for_h = max(o_total - c, 0.0)
        h2o = min(o_for_h, 0.5 * h)
        h2 = max(0.5 * h - h2o, 0.0)
        products.update({
            "CO": co,
            "H2O": h2o,
            "H2": h2,
        })
        return {name: value for name, value in products.items() if value > 0.0}

    if c <= z + eps:
        beta = 1.0
    else:
        beta = max(min((2.0 * o2_in) / max(c - z, eps), 1.0), 0.0)
    products.update({
        "CO": beta * c,
        "H2": beta * 0.5 * h,
        fuel.name: max(1.0 - beta, 0.0),
    })
    return {name: value for name, value in products.items() if value > 0.0}




def _normalize_positive_species(composition: Mapping[str, float]) -> dict[str, float]:
    return {str(name): float(value) for name, value in composition.items() if float(value) > 1e-15}


def _apply_equilibrium_lite_shift(
    composition: Mapping[str, float],
    temperature_K: float = 2200.0,
    strength: float = 0.35,
) -> dict[str, float]:
    """Apply a solver-friendly atom-balanced high-temperature product shift.

    This is intentionally not a full equilibrium solver. It mimics the tendency of hot
    combustion products to redistribute a limited fraction of CO2/H2O into CO/H2/O2
    and, with excess oxygen present, into OH. The closure is bounded, monotonic with
    temperature, and preserves elemental balance exactly.
    """
    comp = {str(k): float(v) for k, v in composition.items() if float(v) > 1e-15}
    T = float(temperature_K)
    if T <= 1200.0:
        return comp
    phi_T = max(0.0, min((T - 1200.0) / 1800.0, 1.0))
    s = max(0.0, min(float(strength), 1.0)) * phi_T
    if s <= 0.0:
        return comp

    # Reaction A: CO2 + H2O <-> CO + H2 + O2
    # Provides a bounded dissociation-like shift for hot gases.
    n_co2 = comp.get('CO2', 0.0)
    n_h2o = comp.get('H2O', 0.0)
    xi_a = min(n_co2, n_h2o) * (0.28 * s)
    if xi_a > 0.0:
        comp['CO2'] = n_co2 - xi_a
        comp['H2O'] = n_h2o - xi_a
        comp['CO'] = comp.get('CO', 0.0) + xi_a
        comp['H2'] = comp.get('H2', 0.0) + xi_a
        comp['O2'] = comp.get('O2', 0.0) + xi_a

    # Reaction B: H2O + 0.5 O2 <-> 2 OH
    # Only active when oxygen is available; bounded to remain robust.
    n_h2o = comp.get('H2O', 0.0)
    n_o2 = comp.get('O2', 0.0)
    xi_b = min(n_h2o, 2.0 * n_o2) * (0.14 * s)
    if xi_b > 0.0:
        comp['H2O'] = n_h2o - xi_b
        comp['O2'] = n_o2 - 0.5 * xi_b
        comp['OH'] = comp.get('OH', 0.0) + 2.0 * xi_b

    return _normalize_positive_species(comp)


def complete_combustion_products(
    fuel_name: str,
    lambda_air: float = 1.0,
    rich_mode: str = "simple",
    equilibrium_lite: bool = False,
    equilibrium_temperature_K: float = 2200.0,
    equilibrium_strength: float = 0.35,
) -> dict[str, float]:
    """Return an atom-balanced product mixture for 1 mol fuel.

    Modes for lambda < 1:
    - ``simple``: complete-combustion products of a lambda-fraction + unburned fuel remainder
    - ``extended``: rich products may include CO and H2, plus residual fuel only when oxygen is very low

    Optional ``equilibrium_lite`` applies a bounded high-temperature redistribution
    of a limited fraction of CO2/H2O into CO/H2/O2/OH. This is not a full equilibrium
    solver, but a robust closure intended for engine-cycle simulations.
    """
    fuel = get_species(fuel_name)
    lam = max(float(lambda_air), 1e-9)
    o2_st = stoich_o2_moles_per_mole_fuel(fuel)
    o2_in = lam * o2_st

    if lam >= 1.0:
        products = _complete_or_lean_products(fuel, o2_in)
    else:
        rich_key = str(rich_mode or "simple").strip().lower()
        if rich_key in {"simple", "legacy"}:
            products = _simple_rich_products(fuel, o2_in, lam)
        elif rich_key in {"extended", "co_h2", "rich_products"}:
            products = _extended_rich_products(fuel, o2_in)
        else:
            raise ValueError(f"Unknown rich combustion products mode: {rich_mode}")

    if equilibrium_lite:
        products = _apply_equilibrium_lite_shift(
            products,
            temperature_K=equilibrium_temperature_K,
            strength=equilibrium_strength,
        )
    return _normalize_positive_species(products)


def combustion_products_mixture(
    fuel_name: str,
    lambda_air: float = 1.0,
    rich_mode: str = "simple",
    equilibrium_lite: bool = False,
    equilibrium_temperature_K: float = 2200.0,
    equilibrium_strength: float = 0.35,
) -> IdealGasMixture:
    return make_mixture(
        complete_combustion_products(
            fuel_name=fuel_name,
            lambda_air=lambda_air,
            rich_mode=rich_mode,
            equilibrium_lite=equilibrium_lite,
            equilibrium_temperature_K=equilibrium_temperature_K,
            equilibrium_strength=equilibrium_strength,
        )
    )
