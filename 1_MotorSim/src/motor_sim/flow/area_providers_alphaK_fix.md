# area_providers.py – Korrektur der alphaK-Interpretation

## Ziel der Änderung

Diese Fassung korrigiert die Auswertung in `ValveAreaProvider`, damit `alphaK`
nicht doppelt über die Ventilanzahl skaliert wird.

## Fachliche Definition

Für das Ventilmodell wird `alphaK` als **gesamtzylinderbezogener Kennwert**
interpretiert. Damit gilt:

\[
A_{eff,total} = \alpha_k \cdot A_{piston}
\]

`alphaK` ist also auf die Kolbenfläche des gesamten Zylinders bezogen und
nicht auf ein Einzelventil.

## Frühere inkonsistente Form

Vorher wurde effektiv gerechnet:

\[
A_{eff,total} = count \cdot \alpha_k \cdot A_{piston}
\]

Das ist nur dann korrekt, wenn `alphaK` explizit **pro Einzelventil** definiert
wäre. Das ist für klassische Motor-Kennfelder normalerweise nicht der Fall.

## Neue konsistente Form

Jetzt gilt:

\[
A_{eff,total} = \alpha_k \cdot A_{piston}
\]

Die Ventilanzahl geht nur in die gesamte geometrische Ventilsitzfläche ein:

\[
A_{valve,total} = count \cdot A_{valve,single}
\]

und damit in die separat ausgewiesene Ventilströmzahl

\[
\alpha_v = \frac{A_{eff,total}}{A_{valve,total}}
\]

## Konsequenzen

- `A_in_eff` und `A_ex_eff` werden kleiner und physikalisch konsistenter.
- Die resultierenden Massenströme sinken entsprechend, da im Nozzle-Modell
  \(\dot m \propto A\) gilt.
- Blowback, Reversion und die allgemeine Druckdynamik werden realistischer.
- Die Steifigkeit des Gesamtsystems kann sich verringern, weil die Ströme
  nicht mehr künstlich mit `count` aufgeblasen werden.

## Neue Diagnose-Signale

Zusätzlich werden ausgegeben:

- `valves__alphaV_in`
- `valves__alphaV_ex`
- `valves__A_in_eff_m2`
- `valves__A_ex_eff_m2`

Damit lassen sich in Debug-Plots direkt vergleichen:

- Ventilhub
- alphaK
- alphaV
- effektive Fläche
- Massenstrom

## Patch-Kern

Alt:

```python
A_in_eff = self.count_in * max(aKi, 0.0) * A_piston
A_ex_eff = self.count_ex * max(aKe, 0.0) * A_piston
```

Neu:

```python
A_in_eff = max(aKi, 0.0) * A_piston
A_ex_eff = max(aKe, 0.0) * A_piston
```

## Interpretation

`count_in` und `count_ex` bleiben wichtig für:

- geometrische Gesamtventilfläche
- Diagnose von `alphaV`

aber nicht für die gesamtzylinderbezogene Auswertung von `alphaK`.
