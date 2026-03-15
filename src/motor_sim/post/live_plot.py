"""Einfacher Live-Plotter für die laufende Simulation.

Das Modul visualisiert während der Integration einen gleitenden Zeitbereich.
Aktuell werden dargestellt:
- ``x`` und ``V`` im oberen Plot
- ``mdot_in`` und ``mdot_out`` im unteren Plot

Refactoring gegenüber der Minimalvariante
----------------------------------------
- ausführliche Klassendokumentation
- kleine Helper für das Puffermanagement
- klarere Trennung zwischen Datenaufnahme und Zeichnen

Hinweis
-------
Dieser Plotter ist absichtlich leichtgewichtig und nutzt Matplotlib im
Interaktivmodus. Für sehr hohe Update-Raten kann später ein Throttling oder ein
Canvas-Blitting ergänzt werden.
"""

from __future__ import annotations

from collections import deque

import matplotlib.pyplot as plt
import numpy as np


class LivePlotter:
    """Visualisiert ausgewählte Signale in einem gleitenden Zeitfenster."""

    def __init__(self, window_s: float = 0.02):
        self.window_s = float(window_s)

        # Zeitverlauf im Ringpuffer-Stil. deque ist für häufiges popleft effizient.
        self.t = deque()
        self.x = deque()
        self.V = deque()
        self.mdot_in = deque()
        self.mdot_out = deque()

        plt.ion()
        self.fig = plt.figure(figsize=(10, 6))
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

        (self.lx,) = self.ax1.plot([], [], label="x")
        (self.lV,) = self.ax1.plot([], [], label="V")
        self.ax1.set_xlabel("t [s]")
        self.ax1.set_ylabel("x [m] / V [m³]")
        self.ax1.grid(True)
        self.ax1.legend(loc="upper right")

        (self.lmi,) = self.ax2.plot([], [], label="ṁ_in")
        (self.lmo,) = self.ax2.plot([], [], label="ṁ_out")
        self.ax2.set_xlabel("t [s]")
        self.ax2.set_ylabel("ṁ [kg/s]")
        self.ax2.grid(True)
        self.ax2.legend(loc="upper right")

        self.fig.tight_layout()

    def _append_sample(self, t: float, signals: dict) -> None:
        """Fügt einen neuen Messpunkt an den Puffer an."""
        self.t.append(float(t))
        self.x.append(float(signals.get("x", 0.0)))
        self.V.append(float(signals.get("V", 0.0)))
        self.mdot_in.append(float(signals.get("mdot_in", 0.0)))
        self.mdot_out.append(float(signals.get("mdot_out", 0.0)))

    def _trim_window(self) -> None:
        """Entfernt alte Werte außerhalb des gleitenden Fensters."""
        if not self.t:
            return
        t_min = self.t[-1] - self.window_s
        while self.t and self.t[0] < t_min:
            self.t.popleft()
            self.x.popleft()
            self.V.popleft()
            self.mdot_in.popleft()
            self.mdot_out.popleft()

    def _redraw(self) -> None:
        """Aktualisiert die Linienobjekte und das Canvas."""
        tt = np.asarray(self.t, dtype=float)
        self.lx.set_data(tt, np.asarray(self.x, dtype=float))
        self.lV.set_data(tt, np.asarray(self.V, dtype=float))
        self.lmi.set_data(tt, np.asarray(self.mdot_in, dtype=float))
        self.lmo.set_data(tt, np.asarray(self.mdot_out, dtype=float))

        self.ax1.relim()
        self.ax1.autoscale_view()
        self.ax2.relim()
        self.ax2.autoscale_view()

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def update(self, t: float, signals: dict) -> None:
        """Nimmt einen neuen Simulationszustand auf und zeichnet ihn."""
        self._append_sample(t, signals)
        self._trim_window()
        self._redraw()
