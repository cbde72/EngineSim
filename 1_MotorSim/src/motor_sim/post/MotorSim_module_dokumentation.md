# MotorSim – Dokumentation und leichte Refaktorierung der hochgeladenen Plot-/Timing-Module

Diese Dokumentation beschreibt die sechs hochgeladenen Dateien, ihren aktuellen Zweck, ihre Schnittstellen, die Datenabhängigkeiten und die vorgenommenen kleinen Refaktorierungen.

## Überblick

Die hochgeladenen Module bilden zusammen den gesamten Postprocessing-Pfad für Ventilereignisse, Overlap, Port-Slots, Live-Plots und Steuerzeiten-Diagramme:

- `steuerdiagramm.py` – dediziertes Steuerzeiten- und Steuerkreisdiagramm
- `valve_events.py` – IVO/IVC/EVO/EVC aus Ventilhub
- `overlap.py` – Überschneidung von Einlass und Auslass
- `slot_events.py` – Port-/Slot-Ereignisse aus Flächen
- `plotting.py` – allgemeine Ergebnisplots inkl. Winkel-/Zeitdarstellung
- `live_plot.py` – interaktiver Laufzeitplotter

---

## 1. `steuerdiagramm.py`

### Aufgabe
Dieses Modul ist das spezialisierteste Plotmodul. Es erzeugt:
- ein kartesisches Steuerzeiten-Diagramm über Kurbelwinkel
- zusätzlich ein klassisches Steuerkreisdiagramm in Polarform

### Erwartete Eingaben
DataFrame-Spalten:
- `theta_deg`
- `V_m3`
- optional `lift_in_mm`
- optional `lift_ex_mm`

Event-Dictionary:
- `IVO_deg`
- `IVC_deg`
- `EVO_deg`
- `EVC_deg`

Optional:
- `overlap`
- `slot_events`
- Fenstergrenzen `plot_theta_min_deg`, `plot_theta_max_deg`

### Interne Struktur
Wichtige Helper:
- `_phase_segments()` – ordnet die Phasen Ansaugen / Verdichten / Arbeiten / Ausschieben dem Winkelbereich zu
- `_wrap_to_window()` – faltet Winkel in das sichtbare Fenster um
- `_prepare_xy()` – macht Signale plotbar
- `_draw_event_labels()` – platziert IVO/IVC/EVO/EVC mit einfacher Kollisionsvermeidung
- `_normalize_segments()` – bereitet Overlap-Segmente für das Sichtfenster auf
- `_draw_tdc_ut_markers()` – setzt OT/UT-Referenzen
- `plot_steuerdiagramm()` – Hauptfunktion für das lineare Diagramm
- `plot_steuerkreisdiagramm()` – Hauptfunktion für das Polar-Diagramm

### Stärken
- gute Trennung von Helpern und eigentlichem Plotaufruf
- hohe Dichte an Layoutwissen an einem Ort
- bereits recht sauber strukturiert

### Schwächen / mögliche nächste Refaktoren
- Fontgrößen und Farben sind als globale Konstanten fest verdrahtet
- es gibt noch kein zentrales `PlotStyle`-Objekt
- Kollisionsreduktion der Event-Labels ist heuristisch und nur eindimensional
- Volume- und Lift-Signale werden einzeln behandelt; ein gemeinsamer `SignalSpec`-Ansatz wäre mittelfristig sauberer

### Durchgeführte leichte Refaktorierung
- Modul-Docstring ergänzt
- viele Helper mit Docstrings versehen
- `_t()` in sprechenderen Namen `_polar_text()` umbenannt
- Kommentare und Strukturblöcke eingeführt
- Verhalten bewusst unverändert gelassen

---

## 2. `valve_events.py`

### Aufgabe
Ermittlung der vier klassischen Ventilereignisse:
- IVO
- IVC
- EVO
- EVC

### Arbeitsweise
Es wird ein einfacher Schwellwertansatz verwendet:
- Ventil offen, wenn `lift > threshold`
- erster Punkt oberhalb des Schwellwertes = Öffnen
- letzter Punkt oberhalb des Schwellwertes = Schließen

### Stärken
- sehr einfach
- gut testbar
- geringe Fehleroberfläche

### Schwächen
- keine Interpolation an der Schwellwertkante
- keine Erkennung mehrerer Öffnungsfenster
- bei verrauschten Signalen potenziell empfindlich

### Durchgeführte leichte Refaktorierung
- Modul-Docstring ergänzt
- robuste Längenprüfung eingebaut
- Parameter und Rückgaben dokumentiert
- Bezeichner `y` → `signal` präzisiert

### Nächster sinnvoller Schritt
Interpolation zwischen zwei Stützstellen, um Öffnungs-/Schließwinkel nicht nur auf Rasterpunkte zu legen.

---

## 3. `overlap.py`

### Aufgabe
Bestimmt Winkelbereiche, in denen Einlass und Auslass gleichzeitig offen sind.

### Arbeitsweise
- Einlass offen: `lift_in_mm > threshold`
- Auslass offen: `lift_ex_mm > threshold`
- Overlap: beide Masken gleichzeitig wahr
- zusammenhängende True-Blöcke werden in Winkelintervalle umgewandelt

### Stärken
- logisch klar
- für Steuerzeitenplot und Reporting direkt brauchbar

### Schwächen
- keine Subsample-Interpolation
- keine gesonderte Behandlung periodischer Masken an Zyklusgrenzen

### Durchgeführte leichte Refaktorierung
- Modul-Docstring
- sprechendere lokale Namen
- strukturierter Return mit klar dokumentierten Feldern

---

## 4. `slot_events.py`

### Aufgabe
Detektiert Port-/Slot-Ereignisse aus effektiven Querschnitten.

### Ausgabearten
Global:
- `INT_OPEN_deg`
- `INT_CLOSE_deg`
- `EXH_OPEN_deg`
- `EXH_CLOSE_deg`
- jeweilige Dauer

Gruppenspezifisch:
- `INT_G*_OPEN_deg`
- `EXH_G*_OPEN_deg`
- Blowdown zwischen Gruppen

### Stärken
- sehr nützlich für Portmotoren oder Slotgeometrien
- globale und gruppenspezifische Sicht in einem Modul

### Schwächen
- Regex-basiertes Gruppenschema ist implizit und nicht zentral definiert
- Öffnungs-/Schließdauer wird nur als `close - open` bestimmt
- keine Behandlung von Mehrfachfenstern pro Gruppe

### Durchgeführte leichte Refaktorierung
- Modul-Docstring und klarere Variablennamen
- Eingabeprüfung auf `theta_deg`
- Logik in Blöcke mit Kommentarcharakter zerlegt

### Nächster sinnvoller Schritt
Ein separates Datenmodell für Slot-Gruppen, z. B. `SlotGroupEvent`, statt ausschließlich flacher Dict-Keys.

---

## 5. `plotting.py`

### Aufgabe
Erzeugt die allgemeine Ergebnisübersicht.

### Enthaltene Darstellungen
- Kolbenweg über Zeit
- Volumen über Zeit
- Kolbenweg über Winkel
- Volumen über Winkel mit zweiter Achse für Hub oder Fläche
- optional p-V-Diagramm

### Rolle relativ zu `steuerdiagramm.py`
`plotting.py` ist die breite Standardübersicht.
`steuerdiagramm.py` ist die spezialisierte Timing-/Valve-Darstellung.

### Stärken
- für einen Blick auf die gesamte Simulation sehr praktisch
- interpoliert zyklische Größen auf ein sauberes Winkelraster

### Schwächen
- mehrere Verantwortlichkeiten in einer Funktion
- Teil duplizierter Steuerzeiten-/Event-Plotlogik im Vergleich zu `steuerdiagramm.py`
- `plt.show()` war für Batch-Läufe ungünstig

### Durchgeführte leichte Refaktorierung
- Hilfsfunktionen `_interp_over_cycle()` und `_add_ot_ut_markers()` eingeführt
- Modul- und Funktionsdocstrings ergänzt
- Figuren am Ende sauber geschlossen
- Verhalten der API beibehalten

### Größter nächster Refaktorschritt
Trennen in:
- Standard-Zeitplots
- Winkelplots
- p-V-Diagramm

Dann könnte `main.py` gezielter entscheiden, welche Grafik wirklich erzeugt werden soll.

---

## 6. `live_plot.py`

### Aufgabe
Echtzeitdarstellung ausgewählter Signale während der Simulation.

### Aktuell geplottete Größen
Oben:
- `x`
- `V`

Unten:
- `mdot_in`
- `mdot_out`

### Stärken
- sehr kompakt
- für Solver-Debugging sofort nützlich
- `deque` ist für Sliding-Window sinnvoll

### Schwächen
- jede Aktualisierung triggert vollständiges Redraw
- kein Downsampling/Throttling
- keine konfigurierbare Signalauswahl

### Durchgeführte leichte Refaktorierung
- Hilfsmethoden `_append_sample()`, `_trim_window()`, `_redraw()` ergänzt
- Legenden hinzugefügt
- ausführliche Klassendokumentation ergänzt

### Nächster sinnvoller Schritt
Update-Frequenz begrenzen, etwa nur jede n-te Solver-Ausgabe zeichnen oder nach Mindestzeitabstand.

---

## Querbewertung der sechs Dateien

### Was bereits gut ist
- Die Module sind funktional relativ klar abgegrenzt.
- Es gibt nur wenig unnötige Klassenkomplexität.
- Der technische Fokus ist erkennbar: Ventilevents, Overlap, Slots, Ergebnisplots.

### Wo mittelfristig Architekturgewinn liegt
1. **Gemeinsame Event-Datentypen**
   Statt freier Dicts für alles wären strukturierte Objekte hilfreich:
   - `ValveEvents`
   - `OverlapInfo`
   - `SlotEvents`

2. **Gemeinsamer Plot-Stil**
   Farben, Fontgrößen, Linienstärken, Marker zentralisieren.

3. **Interpolation an Triggerkanten**
   Sowohl für Ventile als auch Slots würden die Winkel präziser.

4. **Deduplizierung von Plotlogik**
   `plotting.py` und `steuerdiagramm.py` teilen sich Konzepte wie OT/UT, Eventlinien, Winkelraster.

5. **Sauberer Batch-/GUI-Modus**
   Interaktive Anzeige und Dateispeicherung sollten klarer getrennt sein.

---

## Gelieferte Dateien in diesem Paket

- `steuerdiagramm.py` – dokumentiert, leicht bereinigt
- `valve_events.py` – dokumentiert, robustere Eingabeprüfung
- `live_plot.py` – dokumentiert, intern etwas strukturierter
- `overlap.py` – dokumentiert, leicht bereinigt
- `plotting.py` – dokumentiert, kleine interne Helper ergänzt
- `slot_events.py` – dokumentiert, leicht bereinigt

Die Änderungen sind bewusst **leichtgewichtig** gehalten, damit deine aktuelle Referenzbasis nicht unnötig destabilisiert wird.
