# MotorSim NASA Thermodynamic Library

<p align="center">
  <img src="docs/images/motorsim_banner.png" alt="MotorSim NASA Thermodynamic Library" width="100%">
</p>

<p align="center">
  <b>High-performance NASA-7 thermodynamic property library for MotorSim</b><br>
  Temperature-dependent gas properties for air, fuels, and combustion products in engine simulation.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-active-success">
  <img alt="Tests" src="https://img.shields.io/badge/tests-passing-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

---

## Overview

**MotorSim NASA Thermodynamic Library** is a lightweight and extensible thermodynamic property package for
high-speed internal combustion engine simulation.

It provides **temperature-dependent ideal-gas thermodynamics** based on the **NASA 7-coefficient polynomial formulation**, enabling significantly more realistic thermodynamic behavior than constant-property models while preserving the speed required for transient simulation.

The library is designed for integration into **MotorSim V06** and similar 0D / quasi-dimensional simulation environments.

### Key capabilities

- NASA-7 polynomial thermodynamics
- temperature-dependent `cp(T)`, `cv(T)`, `h(T)`, `u(T)`, `s(T)`, `γ(T)`
- air, fuels, radicals, and combustion products
- pure Python implementation with low overhead
- suitable for fast RHS evaluation in engine solvers
- clean API for later extension toward mixtures and real-gas models

---

## Why this library exists

Many reduced engine simulation models still use:

- constant heat capacity
- constant ratio of specific heats
- simplified fuel thermodynamics

These assumptions are fast, but they distort:

- compression temperature
- peak pressure
- expansion work
- combustion temperature level
- exhaust enthalpy
- γ(T) during high-temperature phases

This library closes that gap by introducing **physically meaningful temperature-dependent gas properties**
without the computational cost of full equilibrium chemistry or high-fidelity real-gas packages.

---

## Thermodynamic model

The implementation uses the **NASA-7 polynomial representation**.

### Heat capacity

\[
\frac{c_p(T)}{R} =
a_1 + a_2 T + a_3 T^2 + a_4 T^3 + a_5 T^4
\]

### Enthalpy

\[
\frac{h(T)}{RT} =
a_1 + \frac{a_2}{2}T + \frac{a_3}{3}T^2 + \frac{a_4}{4}T^3 + \frac{a_5}{5}T^4 + \frac{a_6}{T}
\]

### Entropy

\[
\frac{s(T)}{R} =
a_1 \ln T + a_2 T + \frac{a_3}{2}T^2 + \frac{a_4}{3}T^3 + \frac{a_5}{4}T^4 + a_7
\]

### Equation of state

The present library assumes an **ideal gas equation of state**:

\[
p = \rho R T
\]

This means the package provides **realistic caloric properties** but not yet a real-gas compressibility model.

---

## Species coverage

### Air components

- `O2`
- `N2`
- `AR`

### Combustion products and radicals

- `CO2`
- `H2O`
- `CO`
- `H2`
- `OH`
- `O`
- `H`
- `HO2`
- `H2O2`
- `NO`
- `NO2`

### Fuels

- `CH3OH` — Methanol
- `C2H5OH` — Ethanol
- `IC8H18` — Gasoline surrogate (iso-octane)
- `NC12H26` — Diesel surrogate (n-dodecane)
- `H2` — Hydrogen

### Convenience aliases

- `luft`
- `methanol`
- `ethanol`
- `benzin`
- `diesel`
- `wasserstoff`

---

## Repository structure

```text
MotorSim_NASA_Thermo/
├─ src/
│  └─ motor_sim/
│     └─ gas/
│        ├─ nasa7.py
│        └─ nasa7_library.py
├─ tests/
│  └─ test_nasa7_library.py
├─ docs/
│  └─ images/
│     ├─ motorsim_banner.png
│     ├─ architecture.png
│     └─ cp_comparison.png
├─ README.md
└─ LICENSE
