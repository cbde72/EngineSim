# Ausführliche Dokumentation zu `model.py`

## Zweck

`model.py` enthält die zentrale Solverlogik der MotorSim-Basis. Die Datei definiert die Klasse `Model` mit den Methoden `__init__`, `_flow` und `rhs`. Dabei ist `rhs(t, y)` die rechte Seite des vom Integrator gelösten ODE-Systems.

Die Referenzdatei koppelt:

- globalen Kurbelwinkel
- dynamische Ansaug- und Abgasplena
- pro Zylinder einen Zylinder plus Ansaug- und Abgasrunner
- Port-/Ventilströmung
- optionale Verbrennung per Wiebe-Funktion
- umfangreiche Diagnose-/Plot-Signale

## Aufbau der Klasse

Die Datei enthält drei zentrale Methoden:

- `__init__`: speichert Zustandsindex und Kontext
- `_flow`: kapselt die Massenstromberechnung
- `rhs`: formuliert das eigentliche Solver-Gleichungssystem

## Konstruktor

```python
def __init__(self, state_index, ctx):
    self.S = state_index
    self.ctx = ctx
    self.ctx.model_state = state_index