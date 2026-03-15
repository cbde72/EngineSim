# `model.py` – ausführliche Zeile-für-Zeile-Dokumentation

## Zweck der Datei

`model.py` enthält die zentrale rechte Seite des ODE-Systems der MotorSim-Referenzbasis.  
Die Datei koppelt den globalen Winkelzustand, dynamische Plena, pro Zylinder je einen Zylinderzustand sowie Intake-/Exhaust-Runner, die Port-/Ventilströmung und optional die Verbrennung.

Die Kernfunktion ist:

```python
Model.rhs(t, y)
```

Sie liefert für den Integrator den Ableitungsvektor:

\[
\dot y = f(t, y)
\]

---

## Importbereich

```python
import math
import numpy as np
```

- `math` wird für Skalare, insbesondere Winkelumrechnung, genutzt.
- `numpy` wird für Vektoren, Mittelwerte und Summen verwendet.

```python
from motor_sim.flow.nozzle_choked import mdot_nozzle
from motor_sim.flow.simple_orifice import mdot_orifice
from motor_sim.flow.runner_model import effective_area
from motor_sim.flow.throttle_model import throttle_area
from motor_sim.submodels.combustion import wiebe_heat_release
```

Diese Imports kapseln die physikalischen Teilmodelle:

- `mdot_nozzle`: kompressible Düse / gechokte Strömung
- `mdot_orifice`: vereinfachtes Orifice-Modell
- `effective_area`: hydraulische Reduktion von Runner-/Portflächen
- `throttle_area`: wirksame Drosselfläche
- `wiebe_heat_release`: Wärmefreisetzung durch Wiebe-Modell

---

## Klasse `Model`

Die Klasse bildet die rechte Seite des gesamten Differentialgleichungssystems.

### Konstruktor

```python
def __init__(self, state_index, ctx):
    self.S = state_index
    self.ctx = ctx
    self.ctx.model_state = state_index
```

Bedeutung:

- `self.S`: Mapping von symbolischen Zustandsnamen auf numerische Indizes
- `self.ctx`: globaler Kontext mit Gasmodell, Engine, Konfiguration, Zylindern und Signalpuffer
- `ctx.model_state = state_index`: macht das Mapping für andere Projektteile zugänglich

---

## Methode `_flow(...)`

```python
def _flow(self, p_up, T_up, p_dn, T_dn, Cd, A, flow_model, gamma, R):
```

Diese Methode kapselt die Massenstromberechnung für alle Verbindungsstrecken.

### Variante 1: `nozzle_choked`

```python
if flow_model == "nozzle_choked":
    return mdot_nozzle(Cd, A, p_up, T_up, p_dn, gamma, R)
```

Hier wird ein kompressibles Düsenmodell verwendet.  
Das ist für Gaswechsel physikalisch deutlich näher an VK2 Kapitel 10 als ein einfaches inkompressibles Orifice-Modell.

### Variante 2: Orifice-Fallback

```python
min_temperature_K = ...
rho = p_up / (R * max(T_up, min_temperature_K))
dp = max(p_up - p_dn, 0.0)
return mdot_orifice(Cd, A, rho, dp)
```

Mathematisch:

\[
\rho = \frac{p_{up}}{R T_{up}}
\]

\[
\Delta p = \max(p_{up} - p_{dn}, 0)
\]

Dann:

\[
\dot m = f(C_d, A, \rho, \Delta p)
\]

### Wichtige fachliche Konsequenz

Im Fallback wird negative Druckdifferenz abgeschnitten.  
Das bedeutet:

- Vorwärtsströmung wird abgebildet
- Rückströmung wird **nicht** abgebildet

Das ist wichtig, wenn du die Konvention „in den Zylinder positiv, aus dem Zylinder negativ“ später vollständig und konsistent umsetzen willst.

---

## Methode `rhs(t, y)`

Dies ist die zentrale Solverfunktion.

### 1. Lokale Aliase und Rücksetzen der Signale

```python
S = self.S
ctx = self.ctx
ctx.reset_signals()
```

Hier werden nur lokale Kurzformen gesetzt und die Diagnose-Signale geleert.

---

### 2. Globaler Winkelzustand

```python
theta = float(y[S.i("theta")])
omega = ctx.engine.omega_rad_s
dtheta_dt = omega
dy = np.zeros_like(y)
dy[S.i("theta")] = dtheta_dt
```

Damit gilt:

\[
\frac{d\theta}{dt} = \omega
\]

`theta` ist also ein integraler Zustand.

---

### 3. Gasdaten und numerische Schutzwerte

```python
gamma, R, cp, cv = ctx.gas.gamma, ctx.gas.R, ctx.gas.cp, ctx.gas.cv
```

Hier werden die Stoffwerte geladen.

```python
numerics = ...
links = ...
min_temperature_K = ...
min_volume_m3 = ...
min_runner_volume_m3 = ...
min_mass_kg = ...
runner_defaults = ...
```

Diese Werte schützen vor unphysikalischen oder numerisch instabilen Zuständen.

---

## 4. Dynamische Plena

```python
m_int = float(y[S.i("m_int_plenum")]); T_int = float(y[S.i("T_int_plenum")])
m_ex = float(y[S.i("m_ex_plenum")]); T_ex = float(y[S.i("T_ex_plenum")])
V_int = ctx.cfg.plena.intake.volume_m3; V_ex = ctx.cfg.plena.exhaust.volume_m3
p_int = m_int * R * T_int / max(V_int, min_volume_m3)
p_ex = m_ex * R * T_ex / max(V_ex, min_volume_m3)
```

Hier werden Ansaug- und Abgasplenum als dynamische homogene Kontrollvolumina behandelt.

Mathematisch:

\[
p = \frac{mRT}{V}
\]

für beide Plena.

---

## 5. Randbedingungen und Drossel

```python
p_src_in = ...
T_src_in = ...
p_sink_ex = ...
T_sink_ex = ...
```

- `p_src_in`, `T_src_in`: einlassseitige äußere Quelle
- `p_sink_ex`, `T_sink_ex`: abgasseitige äußere Senke

```python
A_feed = ...
Cd_feed = ...
A_throttle = ...
Cd_throttle = ...
```

Hier werden die wirksame Feed-/Drosselfläche und ihre Beiwertparameter bestimmt.

---

## 6. Globale Plenumströme

```python
md_in_feed = self._flow(...)
md_ex_discharge = self._flow(...)
```

- `md_in_feed`: äußere Quelle → Ansaugplenum
- `md_ex_discharge`: Abgasplenum → äußere Senke

Diese beiden Ströme schließen die Plenumbilanzen gegenüber der Außenwelt.

---

## 7. Sammelgrößen für alle Zylinder

```python
dm_int_total_to_runners = 0.0
dm_ex_total_from_runners = 0.0
p_list = []; V_list = []; x_list = []
runner_T_for_discharge = []
```

Diese Größen werden später für Plenumbilanzen und globale Signalwerte gebraucht.

---

## 8. Zylinderschleife

```python
for cyl in ctx.cylinders:
```

Jeder Zylinder besitzt im Modell:

- ein Zylinderkontrollvolumen
- einen Intake-Runner
- einen Exhaust-Runner

---

### 8.1 Zylinderzustände

```python
m = float(y[S.i(f"m__{prefix}")]); T = float(y[S.i(f"T__{prefix}")])
```

Zylinderzustände:

- `m`: Zylindermasse
- `T`: Zylindertemperatur

---

### 8.2 Runnerzustände

```python
m_rin = ...
T_rin = ...
m_rex = ...
T_rex = ...
```

Runnerzustände:

- Intake-Runner: `m_rin`, `T_rin`
- Exhaust-Runner: `m_rex`, `T_rex`

---

### 8.3 Runner-Konfiguration und Volumina

```python
rcfg = cyl.runner_cfg or {}
rin = rcfg.get("intake", {})
rex = rcfg.get("exhaust", {})
V_rin = ...
V_rex = ...
p_rin = m_rin * R * T_rin / V_rin
p_rex = m_rex * R * T_rex / V_rex
```

Die Runner sind ebenfalls homogene Kontrollvolumina mit idealer Gasgleichung.

---

### 8.4 Geometrie und Kinematik

```python
geom = cyl.eval_geometry(theta)
V = float(geom["V_m3"])
dV_dtheta = float(geom["dV_dtheta_m3_per_rad"])
x = float(geom["x_from_tdc_m"])
theta_local_deg = ...
dV_dt = dV_dtheta * dtheta_dt
p = ctx.gas.p_from_mTV(m, T, V)
```

Hier entstehen die wichtigsten Zylindergrößen:

- `V`: aktuelles Zylindervolumen
- `dV_dtheta`: Volumenänderung pro Kurbelwinkel
- `dV_dt`: Volumenänderung pro Zeit
- `x`: Kolbenweg
- `p`: Zylinderdruck

Mathematisch:

\[
\dot V = \frac{dV}{d\theta}\dot\theta
\]

---

### 8.5 Hilfsdaten für Port-/Ventilmodell

```python
aux = {...}
A_in_geom, Cd_in, A_ex_geom, Cd_ex, lift_in_m, lift_ex_m = ...
```

`aux` stellt dem Port-/Ventilmodell zusätzliche Zustandsgrößen zur Verfügung.  
Das Modell liefert zurück:

- geometrische Einlassfläche
- geometrische Auslassfläche
- Einlass-/Auslass-Cd
- optional Einlass-/Auslasshub

---

### 8.6 Hydraulische Reduktion der Flächen

```python
A_in_eff, phi_in = effective_area(...)
A_ex_eff, phi_ex = effective_area(...)
```

Die geometrische Port-/Ventilfläche wird mit Runnerverlusten zu einer wirksamen hydraulischen Fläche reduziert.

`phi_in` und `phi_ex` sind Diagnosefaktoren der Reduktion.

---

### 8.7 Teilströme des Gaswechselpfads

```python
md_plenum_to_rin = ...
md_rin_to_cyl = ...
md_cyl_to_rex = ...
md_rex_to_plenum = ...
```

Die aktuelle Modellstruktur bildet explizit vier gerichtete Teilströme ab:

1. Ansaugplenum → Intake-Runner
2. Intake-Runner → Zylinder
3. Zylinder → Exhaust-Runner
4. Exhaust-Runner → Abgasplenum

Wichtig:  
Das ist noch eine lokale Flussrichtungsformulierung und noch keine allgemeine signed-Portform.

---

### 8.8 Verbrennung

```python
qdot_comb_W = 0.0
xb_comb = 0.0
dq_dtheta_deg = 0.0
comb_cfg = ...
if bool(comb_cfg.get("enabled", False)):
    qdot_per_rad, xb_comb, dq_dtheta_deg = wiebe_heat_release(...)
    qdot_comb_W = qdot_per_rad * dtheta_dt
```

Wenn aktiviert, liefert das Wiebe-Modell:

- Wärmefreisetzung pro Winkel
- Verbrennungsfortschritt `xb`
- Wärmefreisetzung pro Grad

Umrechnung:

\[
\dot Q_{comb} = \frac{dQ}{d\theta}\dot\theta
\]

---

### 8.9 Zylinder-Massenbilanz

```python
dm_dt = md_rin_to_cyl - md_cyl_to_rex
```

Mathematisch:

\[
\frac{dm_{cyl}}{dt} = \dot m_{rin\to cyl} - \dot m_{cyl\to rex}
\]

Einlass vergrößert, Auslass verkleinert die Zylindermasse.

---

### 8.10 Zylinder-Energiebilanz

```python
dE_dt = md_rin_to_cyl * cp * T_rin - md_cyl_to_rex * cp * T - p * dV_dt + qdot_comb_W
```

Mathematisch:

\[
\frac{dE}{dt}
=
\dot m_{in} c_p T_{in}
-
\dot m_{out} c_p T
-
p \dot V
+
\dot Q_{comb}
\]

Das Modell enthält in dieser Referenzdatei **noch keinen expliziten Wandwärmeübergang** in `dE_dt`.

---

### 8.11 Zylinder-Temperaturgleichung

```python
dT_dt = (dE_dt / cv - T * dm_dt) / max(m, min_mass_kg)
```

Mit:

\[
E = m c_v T
\]

ergibt sich:

\[
\frac{dT}{dt}
=
\frac{1}{m}
\left(
\frac{1}{c_v}\frac{dE}{dt}
-
T\frac{dm}{dt}
\right)
\]

---

### 8.12 Intake-Runner-Bilanzen

```python
dm_rin_dt = md_plenum_to_rin - md_rin_to_cyl
dE_rin_dt = md_plenum_to_rin * cp * T_int - md_rin_to_cyl * cp * T_rin
dT_rin_dt = (dE_rin_dt / cv - T_rin * dm_rin_dt) / max(m_rin, min_mass_kg)
```

Mathematisch:

\[
\frac{dm_{rin}}{dt} = \dot m_{plenum\to rin} - \dot m_{rin\to cyl}
\]

---

### 8.13 Exhaust-Runner-Bilanzen

```python
dm_rex_dt = md_cyl_to_rex - md_rex_to_plenum
dE_rex_dt = md_cyl_to_rex * cp * T - md_rex_to_plenum * cp * T_rex
dT_rex_dt = (dE_rex_dt / cv - T_rex * dm_rex_dt) / max(m_rex, min_mass_kg)
```

Mathematisch:

\[
\frac{dm_{rex}}{dt} = \dot m_{cyl\to rex} - \dot m_{rex\to plenum}
\]

---

### 8.14 Sammelgrößen für Plena

```python
dm_int_total_to_runners += md_plenum_to_rin
dm_ex_total_from_runners += md_rex_to_plenum
runner_T_for_discharge.append(T_rex)
```

Diese Größen werden später in den Plenumbilanzen benutzt.

---

### 8.15 Diagnose-Signale pro Zylinder

```python
sig = {...}
ctx.signals.update(sig)
```

Hier werden zahlreiche Diagnosegrößen gespeichert:

- Druck, Temperatur, Masse
- Volumen und Kolbenweg
- Runnerzustände
- Teilmassenströme
- wirksame und geometrische Flächen
- Wandflächen und Wandtemperaturen
- Verbrennungsgrößen
- optional Ventilhübe

Das macht `model.py` zur wichtigsten Quelle für Plotting und Debugging.

---

## 9. Plenumbilanzen

### Ansaugplenum

```python
dm_int_dt = md_in_feed - dm_int_total_to_runners
dE_int_dt = md_in_feed * cp * T_src_in - dm_int_total_to_runners * cp * T_int
dT_int_dt = (dE_int_dt / cv - T_int * dm_int_dt) / max(m_int, min_mass_kg)
```

Mathematisch:

\[
\frac{dm_{int}}{dt} = \dot m_{feed} - \sum \dot m_{int\to runners}
\]

---

### Abgasplenum

```python
mean_T_runner_ex = ...
dm_ex_dt = dm_ex_total_from_runners - md_ex_discharge
dE_ex_dt = dm_ex_total_from_runners * cp * mean_T_runner_ex - md_ex_discharge * cp * T_ex
dT_ex_dt = (dE_ex_dt / cv - T_ex * dm_ex_dt) / max(m_ex, min_mass_kg)
```

Mathematisch:

\[
\frac{dm_{ex}}{dt} = \sum \dot m_{runners\to ex} - \dot m_{discharge}
\]

Die Abgastemperatur wird hier über einen einfachen Mittelwertansatz angenähert.

---

## 10. Generische Kurzsignale

```python
active = ctx.cylinder.name
ctx.signals["theta_deg"] = ...
ctx.signals["p"] = ...
ctx.signals["V"] = ...
ctx.signals["mdot_in"] = ...
ctx.signals["mdot_out"] = ...
...
```

Für GUI und Plotter werden zusätzlich generische Signalnamen des gerade aktiven Zylinders gesetzt.

Außerdem entstehen Mehrzylinder-Sammelwerte wie:

```python
ctx.signals["p_cyl_mean_pa"]
ctx.signals["V_total_m3"]
```

sowie Plenum- und Drosseldiagnosen.

---

## 11. Rückgabe

```python
return dy
```

Am Ende wird der vollständige Ableitungsvektor an den Integrator zurückgegeben.

---

# Fachliche Gesamtbewertung

## Was das Modell schon gut macht

- klare Mehrvolumenstruktur
- modularer Aufbau
- dynamische Plena
- Runnerverluste
- gute Diagnosefähigkeit
- optionale Verbrennung
- saubere Trennung in Teilmodelle

## Was fachlich noch offen ist

- keine vollständige signed-Portform
- Orifice-Fallback ohne Rückströmung
- kein expliziter Wandwärmeübergang in der Energiebilanz
- konstante Stoffwerte
- keine direkte VK2-Formulierung mit expliziten Ein-/Ausstromgleichungen aus Kapitel 10

## Empfohlene nächste Schritte

1. vollständige Vorzeichenkonvention:
   - in den Zylinder positiv
   - aus dem Zylinder negativ

2. `_flow()` auf signed-Ströme erweitern

3. Wandwärmeübergang in `dE_dt` ergänzen

4. Portgleichungen auf VK2 Kapitel 10 normieren

5. Energiegleichung ggf. auf
   \[
   \frac{dU}{dt} = \dot Q - p\dot V + \sum \dot m h
   \]
   umstellen
