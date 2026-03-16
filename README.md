MotorSim NASA Thermodynamic Library

NASA polynomial thermodynamic database for MotorSim V06 including fuels, air components, and combustion products.

The library provides temperature-dependent thermodynamic properties using the NASA-7 polynomial formulation widely used in combustion simulation tools such as
Cantera,
CHEMKIN and
NASA CEA.

It enables accurate modeling of:

temperature dependent heat capacity

enthalpy

entropy

ratio of specific heats

mixture thermodynamics

for internal combustion engine simulations.

Features

✔ NASA-7 polynomial thermodynamics
✔ temperature range up to 6000 K
✔ species database for air, fuels and combustion products
✔ lightweight pure-Python implementation
✔ optimized for high-speed engine simulation loops
✔ compatible with MotorSim V06

Included Species
Air Components
Species	Formula
Oxygen	O₂
Nitrogen	N₂
Argon	Ar
Combustion Products
Species	Formula
Carbon dioxide	CO₂
Water	H₂O
Carbon monoxide	CO
Hydrogen	H₂
OH radical	OH
Atomic oxygen	O
Atomic hydrogen	H
Hydroperoxyl	HO₂
Hydrogen peroxide	H₂O₂
Nitric oxide	NO
Nitrogen dioxide	NO₂
Fuels
Fuel	Surrogate
Methanol	CH₃OH
Ethanol	C₂H₅OH
Gasoline	Iso-octane (C₈H₁₈)
Diesel	n-Dodecane (C₁₂H₂₆)
Hydrogen	H₂

Surrogate fuels are commonly used in combustion simulations to represent complex fuel mixtures.

Thermodynamic Model

The thermodynamic properties follow the NASA 7-coefficient polynomial representation.

Heat Capacity
𝑐
𝑝
(
𝑇
)
𝑅
=
𝑎
1
+
𝑎
2
𝑇
+
𝑎
3
𝑇
2
+
𝑎
4
𝑇
3
+
𝑎
5
𝑇
4
R
c
p
	​

(T)
	​

=a
1
	​

+a
2
	​

T+a
3
	​

T
2
+a
4
	​

T
3
+a
5
	​

T
4
Enthalpy
ℎ
(
𝑇
)
𝑅
𝑇
=
𝑎
1
+
𝑎
2
2
𝑇
+
𝑎
3
3
𝑇
2
+
𝑎
4
4
𝑇
3
+
𝑎
5
5
𝑇
4
+
𝑎
6
𝑇
RT
h(T)
	​

=a
1
	​

+
2
a
2
	​

	​

T+
3
a
3
	​

	​

T
2
+
4
a
4
	​

	​

T
3
+
5
a
5
	​

	​

T
4
+
T
a
6
	​

	​

Entropy
𝑠
(
𝑇
)
𝑅
=
𝑎
1
ln
⁡
𝑇
+
𝑎
2
𝑇
+
𝑎
3
2
𝑇
2
+
𝑎
4
3
𝑇
3
+
𝑎
5
4
𝑇
4
+
𝑎
7
R
s(T)
	​

=a
1
	​

lnT+a
2
	​

T+
2
a
3
	​

	​

T
2
+
3
a
4
	​

	​

T
3
+
4
a
5
	​

	​

T
4
+a
7
	​

Equation of State

The library assumes an ideal gas equation of state:

𝑝
=
𝜌
𝑅
𝑇
p=ρRT

Temperature dependent thermodynamic properties are provided by NASA polynomials.

Installation

Clone the repository

git clone https://github.com/<user>/motorsim-nasa-thermo.git

Install dependencies

pip install numpy
Usage Example
from nasa7_library import get_species

species = get_species("O2")

T = 1200.0

cp = species.cp(T)
h = species.h(T)
gamma = species.gamma(T)

print(cp, h, gamma)
Mixture Example

Example for a simple air mixture.

from nasa7_library import dry_air

air = dry_air()

T = 1000.0

cp = air.cp(T)
gamma = air.gamma(T)
Combustion Products

Example for complete combustion products.

from nasa7_library import complete_combustion_products

products = complete_combustion_products("methanol")

T = 2000

cp = products.cp(T)
Integration with MotorSim

MotorSim can switch between different thermodynamic models:

Mode	Description
constant_cp	constant heat capacity
nasa7	NASA polynomial thermodynamics

Example configuration

{
  "thermodynamics": "nasa7",
  "fuel": "methanol"
}
Performance

NASA polynomials are extremely efficient.

Typical cost per evaluation:

~10 floating point operations

no iteration

no table lookup

Therefore the model is well suited for high-frequency RHS evaluations in engine simulations.

Data Sources

Thermodynamic coefficients are based on datasets used in:

GRI-Mech 3.0 mechanism

n-Dodecane Reitz mechanism

ethanol combustion mechanisms

NASA thermochemical tables

These datasets are also used by:

Cantera

CHEMKIN

NASA CEA

Validation

Basic validation tests verify:

heat capacity curves

enthalpy integration

γ(T) behaviour

Example test run:

pytest tests/test_nasa7_library.py

Expected output:

4 passed
Roadmap

Future improvements may include:

mixture fraction combustion

equilibrium chemistry

real-gas equation of state

tabulated thermodynamic lookup

GPU accelerated evaluation

License

MIT License

Author

MotorSim Development
