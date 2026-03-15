import json
import json
from pathlib import Path
import os
import subprocess
import sys

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QRectF, QEvent, QTimer, Signal, QSettings
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QFont, QPixmap, QBrush
from PySide6.QtWidgets import (
    QDockWidget,
    QGraphicsDropShadowEffect,
    QTreeWidget,
    QTreeWidgetItem,

    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QSizePolicy,
    QTableWidgetSelectionRange,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStackedWidget,
    QToolButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from motor_sim.flow.valve_profiles import ValveProfilesPeriodic
from motor_sim.flow.ports_profiles import AlphaK
from motor_sim.flow.slot_profiles import SlotGeom
from motor_sim.kinematics.crank_slider import CrankSliderKinematics
from motor_sim.gui.config_defaults import get_default_config, normalize_config



LIGHT_STYLESHEET = """
QWidget {
    background: #f5f7fb;
    color: #1f2937;
    font-size: 10pt;
}
QMainWindow {
    background: #eef2f8;
}
QTabWidget::pane {
    border: 1px solid #d8e0ee;
    border-radius: 12px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e8edf7;
    color: #4b5563;
    border: 1px solid #d8e0ee;
    border-bottom: none;
    padding: 10px 16px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 90px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #111827;
    font-weight: 600;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 14px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    color: #334155;
}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QPlainTextEdit, QTableWidget {
    background: #ffffff;
    border: 1px solid #cfd8e6;
    border-radius: 10px;
    padding: 6px 8px;
    selection-background-color: #cfe3ff;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
}
QPushButton {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1d4ed8;
}
QPushButton:pressed {
    background: #1e40af;
}
QScrollArea {
    border: none;
    background: transparent;
}
QFrame[inspectorCard="True"] {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 14px;
}
QToolButton[inspectorToggle="True"] {
    background: transparent;
    border: none;
    color: #0f172a;
    font-weight: 700;
    text-align: left;
    padding: 6px 8px;
}
QToolBar {
    background: #ffffff;
    border: none;
    spacing: 6px;
    padding: 8px;
}
QToolButton {
    background: #edf3ff;
    color: #1e3a8a;
    border-radius: 10px;
    padding: 8px 12px;
    margin: 2px;
    border: 1px solid #d7e5ff;
    font-weight: 600;
}
QToolButton:hover {
    background: #dbeafe;
}
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #d8e0ee;
}
QHeaderView::section {
    background: #eef4ff;
    color: #334155;
    border: none;
    border-right: 1px solid #d8e0ee;
    border-bottom: 1px solid #d8e0ee;
    padding: 6px;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #e5eaf3;
    alternate-background-color: #f8fbff;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #c7d2e5;
    border-radius: 6px;
    min-height: 24px;
    min-width: 24px;
}
QLabel {
    color: #334155;
}
QCheckBox {
    spacing: 8px;
}
"""

DARK_STYLESHEET = """
QWidget {
    background: #0f172a;
    color: #e5e7eb;
    font-size: 10pt;
}
QMainWindow {
    background: #0b1220;
}
QTabWidget::pane {
    border: 1px solid #263246;
    border-radius: 12px;
    background: #111827;
    top: -1px;
}
QTabBar::tab {
    background: #172033;
    color: #cbd5e1;
    border: 1px solid #263246;
    border-bottom: none;
    padding: 10px 16px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 90px;
}
QTabBar::tab:selected {
    background: #111827;
    color: #ffffff;
    font-weight: 600;
}
QGroupBox {
    background: #111827;
    border: 1px solid #263246;
    border-radius: 14px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    color: #dbeafe;
}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QPlainTextEdit, QTableWidget {
    background: #0f172a;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 6px 8px;
    selection-background-color: #1d4ed8;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid #60a5fa;
}
QPushButton {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #3b82f6;
}
QPushButton:pressed {
    background: #1d4ed8;
}
QToolBar {
    background: #111827;
    border: none;
    spacing: 6px;
    padding: 8px;
}
QToolButton {
    background: #172554;
    color: #dbeafe;
    border-radius: 10px;
    padding: 8px 12px;
    margin: 2px;
    border: 1px solid #1e3a8a;
    font-weight: 600;
}
QToolButton:hover {
    background: #1e3a8a;
}
QStatusBar {
    background: #111827;
    border-top: 1px solid #263246;
}
QHeaderView::section {
    background: #172033;
    color: #e5e7eb;
    border: none;
    border-right: 1px solid #263246;
    border-bottom: 1px solid #263246;
    padding: 6px;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #263246;
    alternate-background-color: #0b1220;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 6px;
    min-height: 24px;
    min-width: 24px;
}
QLabel {
    color: #cbd5e1;
}
QCheckBox {
    spacing: 8px;
}
"""

def apply_modern_style(app: QApplication, theme: str = "light") -> None:
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(DARK_STYLESHEET if str(theme).lower() == "dark" else LIGHT_STYLESHEET)


def _set_table_item(table: QTableWidget, row: int, col: int, value) -> None:
    item = QTableWidgetItem("" if value is None else str(value))
    table.setItem(row, col, item)


def _item_text(table: QTableWidget, row: int, col: int, default: str = "") -> str:
    item = table.item(row, col)
    return item.text().strip() if item and item.text() is not None else default


def _item_float(table: QTableWidget, row: int, col: int, default: float = 0.0) -> float:
    txt = _item_text(table, row, col, "")
    if not txt:
        return default
    try:
        return float(txt)
    except ValueError:
        return default


def _item_int(table: QTableWidget, row: int, col: int, default: int = 0) -> int:
    txt = _item_text(table, row, col, "")
    if not txt:
        return default
    try:
        return int(float(txt))
    except ValueError:
        return default


def _load_numeric_table_flexible(path) -> np.ndarray:
    path = Path(path)
    rows: list[list[float]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("//") or line.startswith(";"):
            continue
        normalized = line.replace(";", " ").replace(",", " ").replace("	", " ")
        parts = [part for part in normalized.split() if part]
        if not parts:
            continue
        try:
            rows.append([float(part) for part in parts])
        except ValueError as exc:
            raise ValueError(f"could not parse numeric values in line: {raw}") from exc
    if not rows:
        raise ValueError(f"no numeric rows found in {path}")
    width = max(len(r) for r in rows)
    if width == 0:
        raise ValueError(f"no numeric columns found in {path}")
    padded = []
    for r in rows:
        rr = list(r)
        if len(rr) < width:
            rr.extend([0.0] * (width - len(rr)))
        padded.append(rr)
    return np.asarray(padded, dtype=float)



class FilePathField(QWidget):
    textChanged = Signal(str)

    def __init__(self, text: str = "", dialog_title: str = "Datei auswählen", file_filter: str = "Alle Dateien (*)", select_directory: bool = False, parent=None):
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._file_filter = file_filter
        self._select_directory = bool(select_directory)

        self.line_edit = QLineEdit()
        self.line_edit.setText(str(text))
        self.line_edit.textChanged.connect(self.textChanged)

        self.browse_btn = QToolButton()
        self.browse_btn.setText("...")
        self.browse_btn.setToolTip(dialog_title)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setAutoRaise(False)
        self.browse_btn.setFixedWidth(32)
        self.browse_btn.clicked.connect(self._browse)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self.line_edit, 1)
        lay.addWidget(self.browse_btn, 0)

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str) -> None:
        self.line_edit.setText(str(text))

    def setPlaceholderText(self, text: str) -> None:
        self.line_edit.setPlaceholderText(text)

    def lineEdit(self) -> QLineEdit:
        return self.line_edit

    def _start_dir(self) -> str:
        raw = self.text().strip()
        if raw:
            p = Path(raw).expanduser()
            if p.is_file():
                return str(p.parent)
            if p.is_dir():
                return str(p)
            if p.parent and str(p.parent) not in ("", "."):
                return str(p.parent)
        return str(Path.cwd())

    def _browse(self) -> None:
        if self._select_directory:
            path = QFileDialog.getExistingDirectory(self, self._dialog_title, self._start_dir())
        else:
            path, _ = QFileDialog.getOpenFileName(self, self._dialog_title, self._start_dir(), self._file_filter)
        if path:
            self.setText(path)

class ConfigFieldFactory:
    @staticmethod
    def line(text: str = "") -> QLineEdit:
        w = QLineEdit()
        w.setText(str(text))
        return w

    @staticmethod
    def file_line(text: str = "", dialog_title: str = "Datei auswählen", file_filter: str = "Alle Dateien (*)") -> FilePathField:
        return FilePathField(text=text, dialog_title=dialog_title, file_filter=file_filter)

    @staticmethod
    def dir_line(text: str = "", dialog_title: str = "Ordner auswählen") -> FilePathField:
        return FilePathField(text=text, dialog_title=dialog_title, file_filter="Alle Dateien (*)", select_directory=True)

    @staticmethod
    def combo(values: list[str], current: str) -> QComboBox:
        w = QComboBox()
        w.addItems(values)
        i = max(0, w.findText(str(current)))
        w.setCurrentIndex(i)
        return w

    @staticmethod
    def check(value: bool) -> QCheckBox:
        w = QCheckBox()
        w.setChecked(bool(value))
        return w

    @staticmethod
    def dspin(value: float = 0.0, minv: float = -1e12, maxv: float = 1e12, step: float = 0.001, dec: int = 6) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setDecimals(dec)
        w.setRange(minv, maxv)
        w.setSingleStep(step)
        w.setValue(float(value))
        return w

    @staticmethod
    def ispin(value: int = 0, minv: int = 0, maxv: int = 10_000_000, step: int = 1) -> QSpinBox:
        w = QSpinBox()
        w.setRange(minv, maxv)
        w.setSingleStep(step)
        w.setValue(int(value))
        return w

    @staticmethod
    def spin(value: int = 0, minv: int = 0, maxv: int = 10_000_000, step: int = 1) -> QSpinBox:
        """Alias für Integer-SpinBoxen, damit neue Tabs konsistent ConfigFieldFactory.spin(...) nutzen können."""
        return ConfigFieldFactory.ispin(value=value, minv=minv, maxv=maxv, step=step)



class ValvePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "none"
        self._theta = np.array([], dtype=float)
        self._y1_in = np.array([], dtype=float)
        self._y1_ex = np.array([], dtype=float)
        self._y2_in = np.array([], dtype=float)
        self._y2_ex = np.array([], dtype=float)
        self._events = {}
        self._overlap_segments = []
        self._cycle_deg = 720.0
        self._message = "No preview"
        self._y1_label = "Value"
        self._y2_label = "Value"
        self._legend = ("In", "Ex", "Aux In", "Aux Ex")
        self.node_rect_map = {}
        self.node_click_callback = None
        self.setMinimumHeight(320)

    def set_valve_preview(self, theta_deg, lift_in_mm, lift_ex_mm, ak_in=None, ak_ex=None, cycle_deg: float = 720.0, events: dict | None = None, overlap_segments=None, message: str = "") -> None:
        self._mode = "valves"
        self._theta = np.asarray(theta_deg, dtype=float)
        self._y1_in = np.asarray(lift_in_mm, dtype=float)
        self._y1_ex = np.asarray(lift_ex_mm, dtype=float)
        self._y2_in = np.asarray(ak_in if ak_in is not None else np.zeros_like(self._theta), dtype=float)
        self._y2_ex = np.asarray(ak_ex if ak_ex is not None else np.zeros_like(self._theta), dtype=float)
        self._events = events or {}
        self._overlap_segments = overlap_segments or []
        self._cycle_deg = float(cycle_deg)
        self._message = message
        self._y1_label = "Lift [mm]"
        self._y2_label = "αK [-]"
        self._legend = ("Einlasshub", "Auslasshub", "αK Einlass", "αK Auslass")
        self.update()

    def set_slot_preview(self, theta_deg, area_in_m2, area_ex_m2, ak_in=None, ak_ex=None, cycle_deg: float = 720.0, events: dict | None = None, overlap_segments=None, message: str = "") -> None:
        self._mode = "slots"
        self._theta = np.asarray(theta_deg, dtype=float)
        self._y1_in = np.asarray(area_in_m2, dtype=float)
        self._y1_ex = np.asarray(area_ex_m2, dtype=float)
        self._y2_in = np.asarray(ak_in if ak_in is not None else np.zeros_like(self._theta), dtype=float)
        self._y2_ex = np.asarray(ak_ex if ak_ex is not None else np.zeros_like(self._theta), dtype=float)
        self._events = events or {}
        self._overlap_segments = overlap_segments or []
        self._cycle_deg = float(cycle_deg)
        self._message = message
        self._y1_label = "A [m²]"
        self._y2_label = "αK [-]"
        self._legend = ("Einlassfläche", "Auslassfläche", "αK Einlass", "αK Auslass")
        self.update()

    def set_message(self, message: str) -> None:
        self._mode = "none"
        self._theta = np.array([], dtype=float)
        self._y1_in = np.array([], dtype=float)
        self._y1_ex = np.array([], dtype=float)
        self._y2_in = np.array([], dtype=float)
        self._y2_ex = np.array([], dtype=float)
        self._events = {}
        self._overlap_segments = []
        self._message = message
        self.update()

    def _map(self, x, y, rect, xmin, xmax, ymin, ymax):
        xx = rect.left() + (x - xmin) / max(1e-12, (xmax - xmin)) * rect.width()
        yy = rect.bottom() - (y - ymin) / max(1e-12, (ymax - ymin)) * rect.height()
        return xx, yy

    def _draw_series(self, p: QPainter, rect: QRectF, x, y, pen: QPen, xmin, xmax, ymin, ymax):
        if len(x) < 2:
            return
        p.setPen(pen)
        pts = [self._map(float(xi), float(yi), rect, xmin, xmax, ymin, ymax) for xi, yi in zip(x, y)]
        for i in range(len(pts) - 1):
            p.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i+1][0]), int(pts[i+1][1]))

    
    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        for name, rect in self.node_rect_map.items():
            if rect.contains(pos):
                if self.node_click_callback:
                    self.node_click_callback(name)
                break


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(10, 10, -10, -10)
        p.fillRect(r, QColor("white") if self.palette().window().color().lightness() > 128 else QColor("#111827"))

        title_rect = QRectF(r.left(), r.top(), r.width(), 22)
        plot = QRectF(r.left() + 64, r.top() + 28, r.width() - 96, r.height() - 70)
        fg = QColor("#202020") if self.palette().window().color().lightness() > 128 else QColor("#e5e7eb")
        muted = QColor("#666666") if self.palette().window().color().lightness() > 128 else QColor("#94a3b8")
        grid = QColor("#e6e6e6") if self.palette().window().color().lightness() > 128 else QColor("#243041")
        shade = QColor(191, 219, 254, 70) if self.palette().window().color().lightness() > 128 else QColor(59, 130, 246, 50)
        p.setPen(QPen(fg, 1))
        title = "Ventilvorschau" if self._mode == "valves" else ("Schlitz-Steuerzeiten" if self._mode == "slots" else "Preview")
        p.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, f"{title} 0…{int(self._cycle_deg)}°KW")

        if self._theta.size < 2:
            p.setPen(QPen(muted, 1))
            p.drawRect(plot)
            p.drawText(plot, Qt.AlignCenter, self._message or "No preview")
            return

        xmin, xmax = 0.0, float(self._cycle_deg)
        y1_max = max(1e-9, float(np.nanmax(np.r_[self._y1_in, self._y1_ex])) * 1.10)
        y2_max = max(1e-9, float(np.nanmax(np.r_[self._y2_in, self._y2_ex])) * 1.10)

        p.setPen(QPen(fg, 1))
        p.drawRect(plot)
        for deg in np.arange(0.0, self._cycle_deg + 1e-9, 60.0):
            xx, _ = self._map(float(deg), 0.0, plot, xmin, xmax, 0.0, y1_max)
            p.setPen(QPen(grid, 1, Qt.DashLine))
            p.drawLine(int(xx), int(plot.top()), int(xx), int(plot.bottom()))
            p.setPen(QPen(fg, 1))
            p.drawText(int(xx - 12), int(plot.bottom() + 18), f"{int(deg)}")

        # OT/UT
        for deg, txt, style in [(0.0, "OT", Qt.DashLine), (180.0, "UT", Qt.DotLine), (360.0, "OT", Qt.DashLine), (540.0, "UT", Qt.DotLine), (720.0, "OT", Qt.DashLine)]:
            if deg <= self._cycle_deg + 1e-9:
                xx, _ = self._map(float(deg), 0.0, plot, xmin, xmax, 0.0, y1_max)
                p.setPen(QPen(muted, 1, style))
                p.drawLine(int(xx), int(plot.top()), int(xx), int(plot.bottom()))
                p.setPen(QPen(fg, 1))
                p.drawText(int(xx - 10), int(plot.top() + 14), txt)

        # overlap shading
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shade))
        for a, b in self._overlap_segments:
            a = float(a); b = float(b)
            if b < a:
                x1, _ = self._map(a, 0.0, plot, xmin, xmax, 0.0, y1_max)
                x2, _ = self._map(self._cycle_deg, 0.0, plot, xmin, xmax, 0.0, y1_max)
                p.drawRect(QRectF(x1, plot.top(), x2 - x1, plot.height()))
                x1, _ = self._map(0.0, 0.0, plot, xmin, xmax, 0.0, y1_max)
                x2, _ = self._map(b, 0.0, plot, xmin, xmax, 0.0, y1_max)
                p.drawRect(QRectF(x1, plot.top(), x2 - x1, plot.height()))
            else:
                x1, _ = self._map(a, 0.0, plot, xmin, xmax, 0.0, y1_max)
                x2, _ = self._map(b, 0.0, plot, xmin, xmax, 0.0, y1_max)
                p.drawRect(QRectF(x1, plot.top(), x2 - x1, plot.height()))
        p.setBrush(Qt.NoBrush)

        # axes labels
        p.setPen(QPen(fg, 1))
        p.drawText(int(plot.left() - 52), int(plot.top() + 12), self._y1_label)
        p.drawText(int(plot.right() + 6), int(plot.top() + 12), self._y2_label)

        for frac in [0.0, 0.5, 1.0]:
            yv = frac * y1_max
            _, yy = self._map(0.0, yv, plot, xmin, xmax, 0.0, y1_max)
            p.setPen(QPen(grid, 1))
            p.drawLine(int(plot.left()), int(yy), int(plot.right()), int(yy))
            p.setPen(QPen(fg, 1))
            p.drawText(int(plot.left() - 58), int(yy + 4), f"{yv:.3g}")
            right_val = frac * y2_max
            p.drawText(int(plot.right() + 6), int(yy + 4), f"{right_val:.3g}")

        self._draw_series(p, plot, self._theta, self._y1_in, QPen(QColor("#0066cc"), 2), xmin, xmax, 0.0, y1_max)
        self._draw_series(p, plot, self._theta, self._y1_ex, QPen(QColor("#cc0000"), 2), xmin, xmax, 0.0, y1_max)

        y2_in_scaled = self._y2_in / max(1e-12, y2_max) * y1_max
        y2_ex_scaled = self._y2_ex / max(1e-12, y2_max) * y1_max
        self._draw_series(p, plot, self._theta, y2_in_scaled, QPen(QColor("#00a8ff"), 1, Qt.DashLine), xmin, xmax, 0.0, y1_max)
        self._draw_series(p, plot, self._theta, y2_ex_scaled, QPen(QColor("#ff7f7f"), 1, Qt.DashLine), xmin, xmax, 0.0, y1_max)

        # event markers
        marker_map = [
            ("IVO_deg", "IVO"), ("IVC_deg", "IVC"), ("EVO_deg", "EVO"), ("EVC_deg", "EVC"),
            ("INT_OPEN_deg", "INT open"), ("INT_CLOSE_deg", "INT close"),
            ("EXH_OPEN_deg", "EXH open"), ("EXH_CLOSE_deg", "EXH close"),
        ]
        colors = {
            "IVO_deg": QColor("#0066cc"), "IVC_deg": QColor("#0066cc"),
            "EVO_deg": QColor("#cc0000"), "EVC_deg": QColor("#cc0000"),
            "INT_OPEN_deg": QColor("#0066cc"), "INT_CLOSE_deg": QColor("#0066cc"),
            "EXH_OPEN_deg": QColor("#cc0000"), "EXH_CLOSE_deg": QColor("#cc0000"),
        }
        p.setPen(QPen(fg, 1))
        label_y = plot.bottom() - 6
        x_off = 0
        for key, label in marker_map:
            if key in self._events:
                xx, _ = self._map(float(self._events[key]), 0.0, plot, xmin, xmax, 0.0, y1_max)
                p.setPen(QPen(colors.get(key, fg), 1, Qt.DashLine))
                p.drawLine(int(xx), int(plot.top()), int(xx), int(plot.bottom()))
                p.setPen(QPen(colors.get(key, fg), 1))
                p.drawText(int(xx + 2), int(label_y - x_off % 24), label)
                x_off += 12

        # info block
        info_lines = []
        for key in ("IVO_deg", "IVC_deg", "EVO_deg", "EVC_deg", "INT_OPEN_deg", "INT_CLOSE_deg", "EXH_OPEN_deg", "EXH_CLOSE_deg", "Overlap_deg", "OVERLAP_deg"):
            if key in self._events:
                val = float(self._events[key])
                info_lines.append(f"{key.replace('_deg','')}: {val:.1f}°")
        if info_lines:
            p.setPen(QPen(fg, 1))
            p.drawText(QRectF(plot.left() + 10, plot.top() + 10, 210, 100), Qt.AlignLeft | Qt.AlignTop, "\n".join(info_lines[:8]))

        legend_y = int(r.bottom() - 12)
        legend = [
            (QPen(QColor("#0066cc"), 2), self._legend[0]),
            (QPen(QColor("#cc0000"), 2), self._legend[1]),
            (QPen(QColor("#00a8ff"), 1, Qt.DashLine), self._legend[2]),
            (QPen(QColor("#ff7f7f"), 1, Qt.DashLine), self._legend[3]),
        ]
        xcur = int(plot.left())
        for pen, text in legend:
            p.setPen(pen); p.drawLine(xcur, legend_y, xcur + 20, legend_y)
            p.setPen(QPen(fg, 1)); p.drawText(xcur + 24, legend_y + 4, text)
            xcur += 120
        if self._message:
            p.drawText(int(plot.left() + 520), legend_y + 4, self._message[:90])


class SlotSketchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_cfg = {"intake_groups": [], "exhaust_groups": [], "intake": {}, "exhaust": {}}
        self.node_rect_map = {}
        self.node_click_callback = None
        self.setMinimumHeight(260)

    def set_slot_config(self, slot_cfg: dict) -> None:
        self._slot_cfg = slot_cfg or {}
        self.update()

    def _group_list(self, side_key: str, fallback_key: str) -> list[dict]:
        groups = self._slot_cfg.get(side_key) or []
        if groups:
            return groups
        single = self._slot_cfg.get(fallback_key) or {}
        return [single] if single else []

    
    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        for name, rect in self.node_rect_map.items():
            if rect.contains(pos):
                if self.node_click_callback:
                    self.node_click_callback(name)
                break


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(12, 12, -12, -12)

        p.fillRect(r, QColor("#ffffff"))
        cyl = QRectF(r.left() + 80, r.top() + 10, r.width() - 160, r.height() - 20)
        p.setPen(QPen(QColor("#303030"), 2))
        p.drawRoundedRect(cyl, 10, 10)

        piston_h = max(18.0, cyl.height() * 0.10)
        piston_y = cyl.bottom() - piston_h - 6
        piston = QRectF(cyl.left() + 20, piston_y, cyl.width() - 40, piston_h)
        p.fillRect(piston, QColor("#777777"))

        p.setPen(QPen(QColor("#666666"), 1, Qt.DashLine))
        p.drawLine(cyl.left(), piston.bottom(), cyl.right(), piston.bottom())
        p.drawText(int(cyl.left() - 60), int(piston.bottom() + 5), "UT")

        scale = cyl.height() / max(0.05, 0.04)
        px_per_m = scale

        def draw_groups(groups, color: QColor, side: str):
            x = cyl.left() - 14 if side == "left" else cyl.right() + 4
            width_px = 10
            for g in groups:
                offset = float(g.get("offset_from_ut_m", 0.0))
                height = float(g.get("height_m", 0.0))
                y_bottom = piston.bottom() - offset * px_per_m
                y_top = y_bottom - height * px_per_m
                rect = QRectF(x, y_top, width_px, max(4.0, y_bottom - y_top))
                p.fillRect(rect, color)
                p.setPen(QPen(Qt.black, 1))
                p.drawRect(rect)
                roof = g.get("roof", {}) or {}
                p.drawText(int(rect.x() + (18 if side == "left" else -55)), int(rect.y() + 12), f"{g.get('count', 0)}x")
                p.drawText(int(rect.x() + (18 if side == "left" else -80)), int(rect.y() + 26), str(roof.get("type", "none")))

        draw_groups(self._group_list("intake_groups", "intake"), QColor("#86c5ff"), "left")
        draw_groups(self._group_list("exhaust_groups", "exhaust"), QColor("#ff9a9a"), "right")

        p.setPen(QPen(Qt.black, 1))
        p.drawText(int(cyl.left() - 65), int(cyl.top() + 16), "Einlass")
        p.drawText(int(cyl.right() + 18), int(cyl.top() + 16), "Auslass")
        p.drawText(int(cyl.left() + 10), int(cyl.top() + 18), "Schlitzdarstellung nahe UT")


class BasicTab(QWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_content = QWidget()
        self.layout = QVBoxLayout(self._scroll_content)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(12)
        self._scroll.setWidget(self._scroll_content)
        outer.addWidget(self._scroll)

        if title:
            hdr = QLabel(title)
            hdr.setStyleSheet('font-size: 14pt; font-weight: 700;')
            self.layout.addWidget(hdr)




class CollapsibleSection(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("inspectorCard", True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.toggle = QPushButton(f"▼  {title}")
        self.toggle.setProperty("inspectorToggle", True)
        self.toggle.setFlat(True)
        self.toggle.setCursor(Qt.PointingHandCursor)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(10, 4, 10, 10)
        self.body_layout.setSpacing(8)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        lay.addWidget(self.toggle)
        lay.addWidget(self.body)

        self._expanded = True
        self.toggle.clicked.connect(self.toggle_expanded)

    def toggle_expanded(self):
        self._expanded = not self._expanded
        self.body.setVisible(self._expanded)
        title = self.toggle.text()[2:].strip() if len(self.toggle.text()) > 2 else self.toggle.text()
        self.toggle.setText(("▼  " if self._expanded else "▶  ") + title)

    def set_title(self, title: str):
        self.toggle.setText(("▼  " if self._expanded else "▶  ") + title)

    def matches(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        text_parts = [self.toggle.text().lower()]
        for lab in self.findChildren(QLabel):
            text_parts.append(lab.text().lower())
        for le in self.findChildren(QLineEdit):
            text_parts.append(le.text().lower())
            text_parts.append(le.placeholderText().lower())
        for cb in self.findChildren(QComboBox):
            text_parts.append(cb.currentText().lower())
        return q in " | ".join(text_parts)





class EngineSystemDiagramWidget(QWidget):
    node_rect_map: dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = {}
        self.node_rect_map = {}
        self.node_click_callback = None
        self.setMinimumHeight(420)

    def set_config(self, cfg: dict) -> None:
        self._cfg = dict(cfg or {})
        self.update()

    def _node_rects(self, r: QRectF):
        cols_y = r.center().y()
        w = 150.0
        h = 68.0
        gap = 42.0
        x0 = r.left() + 24.0
        rects = {
            "source": QRectF(x0, cols_y - h / 2, w, h),
            "throttle": QRectF(x0 + (w + gap), cols_y - h / 2, w, h),
            "int_plenum": QRectF(x0 + 2 * (w + gap), cols_y - h / 2, w, h),
            "cylinders": QRectF(x0 + 3 * (w + gap), cols_y - h / 2 - 92, w + 20, h + 184),
            "ex_plenum": QRectF(x0 + 4 * (w + gap) + 20, cols_y - h / 2, w, h),
            "sink": QRectF(x0 + 5 * (w + gap) + 20, cols_y - h / 2, w, h),
        }
        self.node_rect_map = rects
        return rects

    def _draw_node(self, p: QPainter, rect: QRectF, title: str, lines: list[str], fill: QColor, fg: QColor, border: QColor):
        p.setPen(QPen(border, 1.6))
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(fg, 1))
        p.drawText(rect.adjusted(10, 8, -10, -10), Qt.AlignTop | Qt.AlignHCenter, title)
        body = "\n".join(lines)
        p.drawText(rect.adjusted(10, 24, -10, -10), Qt.AlignLeft | Qt.TextWordWrap, body)

    def _draw_arrow(self, p: QPainter, x1, y1, x2, y2, color: QColor, dashed=False):
        pen = QPen(color, 2, Qt.DashLine if dashed else Qt.SolidLine)
        p.setPen(pen)
        p.drawLine(int(x1), int(y1), int(x2), int(y2))
        # arrow head
        dx, dy = (x2 - x1), (y2 - y1)
        L = max((dx * dx + dy * dy) ** 0.5, 1e-9)
        ux, uy = dx / L, dy / L
        px, py = -uy, ux
        ah = 10.0
        aw = 5.0
        hx, hy = x2, y2
        p.drawLine(int(hx), int(hy), int(hx - ah * ux + aw * px), int(hy - ah * uy + aw * py))
        p.drawLine(int(hx), int(hy), int(hx - ah * ux - aw * px), int(hy - ah * uy - aw * py))

    
    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        for name, rect in self.node_rect_map.items():
            if rect.contains(pos):
                if self.node_click_callback:
                    self.node_click_callback(name)
                break


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(12, 12, -12, -12)

        is_light = self.palette().window().color().lightness() > 128
        bg = QColor("#ffffff") if is_light else QColor("#111827")
        fg = QColor("#111827") if is_light else QColor("#e5e7eb")
        muted = QColor("#64748b") if is_light else QColor("#94a3b8")
        grid = QColor("#dbe4f0") if is_light else QColor("#243041")

        p.fillRect(r, bg)
        p.setPen(QPen(grid, 1))
        p.drawRoundedRect(r, 18, 18)
        p.setPen(QPen(fg, 1))
        p.drawText(r.adjusted(12, 8, -12, -8), Qt.AlignTop | Qt.AlignLeft, "Engine system graph")

        rects = self._node_rects(r.adjusted(0, 26, 0, 0))
        cfg = self._cfg or {}
        th = cfg.get("throttle", {})
        pl = cfg.get("plena", {})
        eng = cfg.get("engine", {})
        cyls = cfg.get("user_cylinders", [])
        enabled = [c for c in cyls if c.get("enabled", True)]

        self._draw_node(
            p, rects["source"], "Upstream source",
            [
                f"p={float(th.get('p_upstream_pa', 101325.0)):.0f} Pa",
                f"T={float(th.get('T_upstream_K', 300.0)):.1f} K",
            ],
            QColor("#eef6ff") if is_light else QColor("#10213c"),
            fg, QColor("#93c5fd")
        )

        amax = float(th.get("A_max_m2", 0.0) or 0.0)
        d = float(th.get("diameter_m", 0.0) or 0.0)
        self._draw_node(
            p, rects["throttle"], "Throttle",
            [
                f"enabled={'yes' if th.get('enabled', False) else 'no'}",
                f"pos={float(th.get('position', 0.0)):.2f}",
                f"Cd={float(th.get('cd', 0.0)):.2f}",
                f"d={d:.3f} m" if d > 0 else f"Amax={amax:.6f} m²",
            ],
            QColor("#effdf5") if is_light else QColor("#0f2a1f"),
            fg, QColor("#86efac")
        )

        pin = pl.get("intake", {})
        self._draw_node(
            p, rects["int_plenum"], "Intake plenum",
            [
                f"V={float(pin.get('volume_m3', 0.0)):.5f} m³",
                f"p0={float(pin.get('p0_pa', 0.0)):.0f} Pa",
                f"T0={float(pin.get('T0_K', 0.0)):.1f} K",
            ],
            QColor("#f5f3ff") if is_light else QColor("#1e1b4b"),
            fg, QColor("#a78bfa")
        )

        p.setPen(QPen(QColor("#f59e0b"), 1.4))
        p.setBrush(QBrush(QColor("#fffbeb") if is_light else QColor("#3a2d12")))
        p.drawRoundedRect(rects["cylinders"], 16, 16)
        p.setPen(QPen(fg, 1))
        p.drawText(rects["cylinders"].adjusted(10, 8, -10, -10), Qt.AlignTop | Qt.AlignHCenter, "Cylinder bank")

        # Draw cylinders inside bank
        bank = rects["cylinders"].adjusted(18, 34, -18, -18)
        cyl_h = 54.0
        gap = 16.0
        max_show = min(len(enabled), 4)
        for i in range(max_show):
            c = enabled[i]
            cy = bank.top() + i * (cyl_h + gap)
            crect = QRectF(bank.left(), cy, bank.width(), cyl_h)
            p.setPen(QPen(QColor("#f59e0b"), 1.1))
            p.setBrush(QBrush(QColor("#fff7ed") if is_light else QColor("#2b1c0d")))
            p.drawRoundedRect(crect, 12, 12)
            rn = c.get("runners", {})
            rin = rn.get("intake", {})
            rex = rn.get("exhaust", {})
            p.setPen(QPen(fg, 1))
            line1 = f"{c.get('name', f'cyl_{i+1}')} | off={float(c.get('crank_angle_offset_deg', 0.0)):.1f}°KW"
            line2 = f"in L={float(rin.get('length_m',0.0)):.3f} / ex L={float(rex.get('length_m',0.0)):.3f}"
            p.drawText(crect.adjusted(10, 6, -10, -8), Qt.AlignLeft | Qt.AlignTop, line1)
            p.setPen(QPen(muted, 1))
            p.drawText(crect.adjusted(10, 26, -10, -8), Qt.AlignLeft | Qt.AlignTop, line2)

        if len(enabled) > max_show:
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(bank.left(), bank.bottom() - 18, bank.width(), 18), Qt.AlignCenter, f"+ {len(enabled) - max_show} more cylinder(s)")

        pex = pl.get("exhaust", {})
        self._draw_node(
            p, rects["ex_plenum"], "Exhaust plenum",
            [
                f"V={float(pex.get('volume_m3', 0.0)):.5f} m³",
                f"p0={float(pex.get('p0_pa', 0.0)):.0f} Pa",
                f"T0={float(pex.get('T0_K', 0.0)):.1f} K",
            ],
            QColor("#fef2f2") if is_light else QColor("#3a1414"),
            fg, QColor("#fca5a5")
        )

        man = cfg.get("manifolds", {})
        self._draw_node(
            p, rects["sink"], "Downstream sink",
            [
                f"p={float(man.get('p_ex_pa', 0.0)):.0f} Pa",
                f"T={float(man.get('T_ex_K', 0.0)):.1f} K",
            ],
            QColor("#f8fafc") if is_light else QColor("#1f2937"),
            fg, QColor("#cbd5e1")
        )

        # arrows main
        self._draw_arrow(p, rects["source"].right(), rects["source"].center().y(), rects["throttle"].left(), rects["throttle"].center().y(), QColor("#3b82f6"))
        self._draw_arrow(p, rects["throttle"].right(), rects["throttle"].center().y(), rects["int_plenum"].left(), rects["int_plenum"].center().y(), QColor("#10b981"))
        self._draw_arrow(p, rects["int_plenum"].right(), rects["int_plenum"].center().y(), rects["cylinders"].left(), rects["cylinders"].center().y(), QColor("#8b5cf6"))
        self._draw_arrow(p, rects["cylinders"].right(), rects["cylinders"].center().y(), rects["ex_plenum"].left(), rects["ex_plenum"].center().y(), QColor("#f59e0b"))
        self._draw_arrow(p, rects["ex_plenum"].right(), rects["ex_plenum"].center().y(), rects["sink"].left(), rects["sink"].center().y(), QColor("#ef4444"))

        # notes footer
        footer = QRectF(r.left() + 14, r.bottom() - 26, r.width() - 28, 18)
        p.setPen(QPen(muted, 1))
        p.drawText(footer, Qt.AlignLeft | Qt.AlignVCenter, f"cycle={eng.get('cycle_type', '-')} | enabled cylinders={len(enabled)} | gas exchange={cfg.get('gasexchange',{}).get('mode','-')}")






class TimingDiagramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = {}
        self._message = "No timing data"
        self._series = {}
        self.setMinimumHeight(430)

    def set_config(self, cfg: dict) -> None:
        self._cfg = dict(cfg or {})
        self._rebuild()
        self.update()

    def set_message(self, msg: str) -> None:
        self._message = msg
        self._series = {}
        self.update()

    def _segments_from_mask(self, theta, mask):
        segs = []
        if len(theta) < 2:
            return segs
        start = None
        prev = False
        for i, ok in enumerate(mask):
            ok = bool(ok)
            if ok and not prev:
                start = i
            if prev and not ok and start is not None:
                segs.append((float(theta[start]), float(theta[i - 1])))
                start = None
            prev = ok
        if prev and start is not None:
            segs.append((float(theta[start]), float(theta[-1])))
        return segs

    def _resolve(self, path_str: str) -> Path:
        p = Path(str(path_str))
        if p.is_absolute():
            return p
        return Path.cwd() / p

    def _sum_segment_durations(self, segments):
        return float(sum(max(0.0, b - a) for a, b in segments))

    def _first_last(self, segments):
        if not segments:
            return None, None
        return float(segments[0][0]), float(segments[-1][1])

    def _midpoints(self, segments):
        return [0.5 * (float(a) + float(b)) for a, b in segments]

    def _build_metrics(self, mode, cycle_deg, a_segments, b_segments, c_segments=None, blowdown_segments=None, scavenge_segments=None):
        metrics = {
            "mode": mode,
            "cycle_deg": float(cycle_deg),
            "a_open_total_deg": self._sum_segment_durations(a_segments),
            "b_open_total_deg": self._sum_segment_durations(b_segments),
            "a_start_deg": self._first_last(a_segments)[0],
            "a_end_deg": self._first_last(a_segments)[1],
            "b_start_deg": self._first_last(b_segments)[0],
            "b_end_deg": self._first_last(b_segments)[1],
            "a_mid_deg": self._midpoints(a_segments)[0] if self._midpoints(a_segments) else None,
            "b_mid_deg": self._midpoints(b_segments)[0] if self._midpoints(b_segments) else None,
        }
        if c_segments is not None:
            metrics["overlap_total_deg"] = self._sum_segment_durations(c_segments)
            metrics["overlap_start_deg"] = self._first_last(c_segments)[0]
            metrics["overlap_end_deg"] = self._first_last(c_segments)[1]
            mids = self._midpoints(c_segments)
            metrics["overlap_mid_deg"] = mids[0] if mids else None
        if blowdown_segments is not None:
            metrics["blowdown_total_deg"] = self._sum_segment_durations(blowdown_segments)
            metrics["blowdown_start_deg"] = self._first_last(blowdown_segments)[0]
            metrics["blowdown_end_deg"] = self._first_last(blowdown_segments)[1]
            mids = self._midpoints(blowdown_segments)
            metrics["blowdown_mid_deg"] = mids[0] if mids else None
        if scavenge_segments is not None:
            metrics["scavenge_total_deg"] = self._sum_segment_durations(scavenge_segments)
            metrics["scavenge_start_deg"] = self._first_last(scavenge_segments)[0]
            metrics["scavenge_end_deg"] = self._first_last(scavenge_segments)[1]
            mids = self._midpoints(scavenge_segments)
            metrics["scavenge_mid_deg"] = mids[0] if mids else None
        return metrics

    def _rebuild(self):
        try:
            cfg = self._cfg
            eng = cfg.get("engine", {})
            cycle_deg = 720.0 if str(eng.get("cycle_type", "4T")).upper() == "4T" else 360.0
            gx = cfg.get("gasexchange", {})
            mode = str(gx.get("mode", "valves"))
            theta = np.linspace(0.0, cycle_deg, int(max(361, cycle_deg * 2 + 1)))

            if mode == "valves":
                v = gx.get("valves", {})
                lift_file = self._resolve(v.get("lift_file", ""))
                ak_file = self._resolve(v.get("alphak_file", ""))
                if not lift_file.exists() or not ak_file.exists():
                    self.set_message(f"Valve timing files missing:\n{lift_file}\n{ak_file}")
                    return
                prof = ValveProfilesPeriodic.from_files(
                    lift_file=str(lift_file),
                    alphak_file=str(ak_file),
                    intake_open=v["intake_open"],
                    exhaust_open=v["exhaust_open"],
                    scaling=v["scaling"],
                    lift_angle_basis=v["lift_angle_basis"],
                    cam_to_crank_ratio=v["cam_to_crank_ratio"],
                    effective_lift_threshold_mm=v["effective_lift_threshold_mm"],
                    cycle_deg=cycle_deg,
                )
                lin, lex = [], []
                for th in theta:
                    li, le = prof.lifts_m(float(th))
                    lin.append(1e3 * li)
                    lex.append(1e3 * le)
                lin = np.asarray(lin, dtype=float)
                lex = np.asarray(lex, dtype=float)
                thr = float(v.get("effective_lift_threshold_mm", 0.1))
                in_open = lin > thr
                ex_open = lex > thr
                overlap = in_open & ex_open
                a_segments = self._segments_from_mask(theta, in_open)
                b_segments = self._segments_from_mask(theta, ex_open)
                c_segments = self._segments_from_mask(theta, overlap)
                self._series = {
                    "mode": "valves",
                    "cycle_deg": cycle_deg,
                    "theta": theta,
                    "curve_a": lin,
                    "curve_b": lex,
                    "curve_a_label": "lift_in_mm",
                    "curve_b_label": "lift_ex_mm",
                    "lane_a_label": "Intake",
                    "lane_b_label": "Exhaust",
                    "lane_c_label": "Valve overlap",
                    "a_segments": a_segments,
                    "b_segments": b_segments,
                    "c_segments": c_segments,
                    "metrics": self._build_metrics("valves", cycle_deg, a_segments, b_segments, c_segments=c_segments),
                    "message": f"Valve timing | threshold={thr:.3f} mm",
                }
                return

            if mode == "ports":
                p_cfg = gx.get("ports", {})
                area_file = self._resolve(p_cfg.get("area_file", ""))
                ak_file = self._resolve(p_cfg.get("alphak_file", ""))
                if not area_file.exists():
                    self.set_message(f"Ports area file missing:\n{area_file}")
                    return
                try:
                    arr = _load_numeric_table_flexible(area_file)
                    if arr.ndim == 1:
                        arr = np.atleast_2d(arr)
                    if arr.shape[1] >= 4:
                        th_in = np.asarray(arr[:, 0], dtype=float)
                        a_in = np.asarray(arr[:, 1], dtype=float)
                        th_ex = np.asarray(arr[:, 2], dtype=float)
                        a_ex = np.asarray(arr[:, 3], dtype=float)
                        a_in_curve = np.interp(theta, th_in, a_in, left=0.0, right=0.0)
                        a_ex_curve = np.interp(theta, th_ex, a_ex, left=0.0, right=0.0)
                    elif arr.shape[1] == 3:
                        th = np.asarray(arr[:, 0], dtype=float)
                        a_in_curve = np.interp(theta, th, np.asarray(arr[:, 1], dtype=float), left=0.0, right=0.0)
                        a_ex_curve = np.interp(theta, th, np.asarray(arr[:, 2], dtype=float), left=0.0, right=0.0)
                    else:
                        th = np.asarray(arr[:, 0], dtype=float)
                        a_tot = np.interp(theta, th, np.asarray(arr[:, 1], dtype=float), left=0.0, right=0.0)
                        a_in_curve = a_tot.copy()
                        a_ex_curve = a_tot.copy()

                    thr = max(1e-12, 0.01 * float(np.nanmax(np.r_[a_in_curve, a_ex_curve, [1e-12]])))
                    in_open = a_in_curve > thr
                    ex_open = a_ex_curve > thr
                    blowdown = ex_open & (~in_open)
                    scavenge = in_open & ex_open

                    a_segments = self._segments_from_mask(theta, in_open)
                    b_segments = self._segments_from_mask(theta, ex_open)
                    blowdown_segments = self._segments_from_mask(theta, blowdown)
                    scavenge_segments = self._segments_from_mask(theta, scavenge)

                    self._series = {
                        "mode": "ports",
                        "cycle_deg": cycle_deg,
                        "theta": theta,
                        "curve_a": a_in_curve,
                        "curve_b": a_ex_curve,
                        "curve_a_label": "A_in_port",
                        "curve_b_label": "A_ex_port",
                        "lane_a_label": "Intake ports",
                        "lane_b_label": "Exhaust ports",
                        "lane_c_label": "Blowdown / Scavenge",
                        "a_segments": a_segments,
                        "b_segments": b_segments,
                        "blowdown_segments": blowdown_segments,
                        "scavenge_segments": scavenge_segments,
                        "metrics": self._build_metrics("ports", cycle_deg, a_segments, b_segments, blowdown_segments=blowdown_segments, scavenge_segments=scavenge_segments),
                        "message": f"Ports timing | threshold={thr:.3e} m² | file={area_file.name}" + (f" | alphaK={ak_file.name}" if ak_file.exists() else ""),
                    }
                    return
                except Exception as exc:
                    self.set_message(f"Ports timing parse error:\n{exc}")
                    return

            if mode == "slots":
                cyls = cfg.get("user_cylinders", [])
                active_name = cfg.get("active_user_cylinder", "")
                _active = next((c for c in cyls if c.get("name") == active_name), cyls[0] if cyls else {})
                slots = gx.get("slots", {})
                intake = slots.get("intake", {})
                exhaust = slots.get("exhaust", {})
                bore = float(eng.get("bore_m", 0.086))
                stroke = float(eng.get("stroke_m", 0.086))
                rod = float(eng.get("conrod_m", max(stroke * 1.5, 1e-6)))
                cr = float(eng.get("compression_ratio", 10.0))
                try:
                    kin = CrankSliderKinematics(
                        bore_m=bore,
                        stroke_m=stroke,
                        conrod_m=rod,
                        compression_ratio=cr,
                    )
                    x = []
                    for th in theta:
                        _, _, xi = kin.volume_dVdtheta_x(np.deg2rad(float(th)))
                        x.append(float(xi))
                    x = np.asarray(x, dtype=float)

                    def slot_curve(scfg):
                        width = float(scfg.get("width_m", 0.0))
                        height = float(scfg.get("height_m", 0.0))
                        count = int(scfg.get("count", 0) or 0)
                        offset_ut = float(scfg.get("offset_from_ut_m", 0.0) or 0.0)
                        roof_from_tdc = max(0.0, min(stroke, stroke - offset_ut))
                        open_h = np.clip(x - roof_from_tdc, 0.0, max(height, 0.0))
                        return np.maximum(0.0, width * count * open_h)

                    a_in_curve = slot_curve(intake)
                    a_ex_curve = slot_curve(exhaust)
                    thr = max(1e-12, 0.01 * float(np.nanmax(np.r_[a_in_curve, a_ex_curve, [1e-12]])))
                    in_open = a_in_curve > thr
                    ex_open = a_ex_curve > thr
                    blowdown = ex_open & (~in_open)
                    scavenge = in_open & ex_open

                    a_segments = self._segments_from_mask(theta, in_open)
                    b_segments = self._segments_from_mask(theta, ex_open)
                    blowdown_segments = self._segments_from_mask(theta, blowdown)
                    scavenge_segments = self._segments_from_mask(theta, scavenge)

                    self._series = {
                        "mode": "slots",
                        "cycle_deg": cycle_deg,
                        "theta": theta,
                        "curve_a": a_in_curve,
                        "curve_b": a_ex_curve,
                        "curve_a_label": "A_in_slot",
                        "curve_b_label": "A_ex_slot",
                        "lane_a_label": "Intake slots",
                        "lane_b_label": "Exhaust slots",
                        "lane_c_label": "Blowdown / Scavenge",
                        "a_segments": a_segments,
                        "b_segments": b_segments,
                        "blowdown_segments": blowdown_segments,
                        "scavenge_segments": scavenge_segments,
                        "metrics": self._build_metrics("slots", cycle_deg, a_segments, b_segments, blowdown_segments=blowdown_segments, scavenge_segments=scavenge_segments),
                        "message": (
                            f"Slots timing | threshold={thr:.3e} m² | "
                            f"in offset_UT={float(intake.get('offset_from_ut_m', 0.0)):.4f} m | "
                            f"ex offset_UT={float(exhaust.get('offset_from_ut_m', 0.0)):.4f} m"
                        ),
                    }
                    return
                except Exception as exc:
                    self.set_message(f"Slots timing build error:\n{exc}")
                    return

            self.set_message(f"Unsupported gasexchange.mode={mode}")
        except Exception as exc:
            self.set_message(f"Timing rebuild error: {exc}")

    def _map(self, x, y, rect, xmin, xmax, ymin, ymax):
        xx = rect.left() + (x - xmin) / max(1e-12, (xmax - xmin)) * rect.width()
        yy = rect.bottom() - (y - ymin) / max(1e-12, (ymax - ymin)) * rect.height()
        return xx, yy

    def _fmt(self, value, unit="°"):
        if value is None:
            return "—"
        return f"{float(value):.1f}{unit}"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(10, 10, -10, -10)
        is_light = self.palette().window().color().lightness() > 128
        bg = QColor("#ffffff") if is_light else QColor("#111827")
        fg = QColor("#111827") if is_light else QColor("#e5e7eb")
        muted = QColor("#64748b") if is_light else QColor("#94a3b8")
        grid = QColor("#dbe4f0") if is_light else QColor("#243041")
        p.fillRect(r, bg)
        p.setPen(QPen(grid, 1))
        p.drawRoundedRect(r, 16, 16)

        title_rect = QRectF(r.left() + 12, r.top() + 8, r.width() - 24, 20)
        p.setPen(QPen(fg, 1))
        p.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, "Timing diagram (720° / 360°)")

        if not self._series:
            p.setPen(QPen(muted, 1))
            p.drawText(r.adjusted(20, 36, -20, -20), Qt.AlignCenter, self._message)
            return

        cycle_deg = float(self._series.get("cycle_deg", 720.0))
        plot = QRectF(r.left() + 52, r.top() + 42, r.width() - 350, r.height() - 86)
        metrics_rect = QRectF(plot.right() + 18, plot.top(), r.right() - plot.right() - 28, plot.height())

        p.setPen(QPen(grid, 1))
        p.drawRect(plot)
        p.drawRoundedRect(metrics_rect, 12, 12)

        # x-grid every 60°
        for deg in np.arange(0.0, cycle_deg + 1e-9, 60.0):
            x, _ = self._map(deg, 0.0, plot, 0.0, cycle_deg, 0.0, 1.0)
            p.setPen(QPen(grid, 1, Qt.DashLine))
            p.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))
            p.setPen(QPen(fg, 1))
            p.drawText(int(x - 12), int(plot.bottom() + 18), f"{int(deg)}")

        markers = [(0, "OT", Qt.DashLine), (180, "UT", Qt.DotLine), (360, "OT", Qt.DashLine)]
        if cycle_deg > 360.0:
            markers += [(540, "UT", Qt.DotLine), (720, "OT", Qt.DashLine)]
        for deg, label, style in markers:
            if deg <= cycle_deg:
                x, _ = self._map(float(deg), 0.0, plot, 0.0, cycle_deg, 0.0, 1.0)
                p.setPen(QPen(muted, 1, style))
                p.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))
                p.setPen(QPen(fg, 1))
                p.drawText(int(x - 10), int(plot.top() + 14), label)

        lane_h = plot.height() / 3.2
        y_a_top = plot.top() + 16
        y_b_top = y_a_top + lane_h + 20
        y_c_top = y_b_top + lane_h + 20

        lane_defs = [
            (self._series.get("lane_a_label", "A"), y_a_top, QColor(59, 130, 246, 70) if is_light else QColor(59, 130, 246, 120)),
            (self._series.get("lane_b_label", "B"), y_b_top, QColor(239, 68, 68, 70) if is_light else QColor(239, 68, 68, 120)),
            (self._series.get("lane_c_label", "C"), y_c_top, QColor(168, 85, 247, 70) if is_light else QColor(168, 85, 247, 120)),
        ]
        for label, yt, fill in lane_defs:
            rect_lane = QRectF(plot.left() + 2, yt, plot.width() - 4, lane_h)
            p.setPen(QPen(grid, 1))
            p.setBrush(QBrush(QColor(fill.red(), fill.green(), fill.blue(), 16 if is_light else 22)))
            p.drawRoundedRect(rect_lane, 8, 8)
            p.setPen(QPen(fg, 1))
            short = label.split()[0] if label else "-"
            p.drawText(int(plot.left() - 50), int(yt + 18), short)

        def draw_segments(segments, ytop, fill):
            if not segments:
                return
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(fill))
            for a, b in segments:
                x1, _ = self._map(a, 0.0, plot, 0.0, cycle_deg, 0.0, 1.0)
                x2, _ = self._map(b, 0.0, plot, 0.0, cycle_deg, 0.0, 1.0)
                p.drawRoundedRect(QRectF(x1, ytop + 6, max(2.0, x2 - x1), lane_h - 12), 8, 8)

        draw_segments(self._series.get("a_segments", []), y_a_top, QColor("#3b82f6"))
        draw_segments(self._series.get("b_segments", []), y_b_top, QColor("#ef4444"))

        if "scavenge_segments" in self._series or "blowdown_segments" in self._series:
            draw_segments(self._series.get("blowdown_segments", []), y_c_top, QColor("#f59e0b"))
            draw_segments(self._series.get("scavenge_segments", []), y_c_top, QColor("#a855f7"))
        else:
            draw_segments(self._series.get("c_segments", []), y_c_top, QColor("#a855f7"))

        theta = self._series.get("theta", np.array([]))
        curve_a = np.asarray(self._series.get("curve_a", []), dtype=float)
        curve_b = np.asarray(self._series.get("curve_b", []), dtype=float)
        max_l = max(1e-12, float(np.nanmax(np.r_[curve_a, curve_b, [1e-12]])))

        def draw_trace(vals, ytop, color):
            if len(vals) != len(theta):
                return
            p.setPen(QPen(QColor(color), 2))
            pts = []
            for th, v in zip(theta, vals):
                x, _ = self._map(float(th), 0.0, plot, 0.0, cycle_deg, 0.0, 1.0)
                yy = (ytop + lane_h - 8) - (float(v) / max_l) * (lane_h - 18)
                pts.append((x, yy))
            for i in range(len(pts) - 1):
                p.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i + 1][0]), int(pts[i + 1][1]))

        draw_trace(curve_a, y_a_top, "#1d4ed8")
        draw_trace(curve_b, y_b_top, "#b91c1c")

        # legend
        lx = plot.right() - 230
        ly = plot.top() + 14

        def legend_line(y, color, label):
            p.setPen(QPen(QColor(color), 2))
            p.drawLine(int(lx), int(y), int(lx + 24), int(y))
            p.setPen(QPen(fg, 1))
            p.drawText(int(lx + 30), int(y + 4), str(label))

        legend_line(ly, "#1d4ed8", self._series.get("curve_a_label", "curve_a"))
        legend_line(ly + 20, "#b91c1c", self._series.get("curve_b_label", "curve_b"))

        if "scavenge_segments" in self._series or "blowdown_segments" in self._series:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#f59e0b")))
            p.drawRoundedRect(QRectF(lx, ly + 32, 24, 10), 4, 4)
            p.setPen(QPen(fg, 1))
            p.drawText(int(lx + 30), int(ly + 42), "blowdown")
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#a855f7")))
            p.drawRoundedRect(QRectF(lx, ly + 52, 24, 10), 4, 4)
            p.setPen(QPen(fg, 1))
            p.drawText(int(lx + 30), int(ly + 62), "scavenge")
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#a855f7")))
            p.drawRoundedRect(QRectF(lx, ly + 32, 24, 10), 4, 4)
            p.setPen(QPen(fg, 1))
            p.drawText(int(lx + 30), int(ly + 42), "overlap")

        p.setPen(QPen(fg, 1))
        p.drawText(QRectF(plot.left(), plot.bottom() + 22, plot.width(), 18), Qt.AlignLeft, self._series.get("message", ""))

        # metrics panel
        m = self._series.get("metrics", {})
        p.setPen(QPen(fg, 1))
        p.drawText(metrics_rect.adjusted(12, 8, -12, -8), Qt.AlignTop | Qt.AlignLeft, "Timing metrics")

        lines = []
        mode = m.get("mode", "-")
        lines.append(f"mode: {mode}")
        lines.append(f"cycle: {float(m.get('cycle_deg', 0.0)):.0f}°KW")
        lines.append("")
        lines.append(f"A start: {self._fmt(m.get('a_start_deg'))}")
        lines.append(f"A end:   {self._fmt(m.get('a_end_deg'))}")
        lines.append(f"A dur.:  {self._fmt(m.get('a_open_total_deg'))}")
        lines.append(f"A mid:   {self._fmt(m.get('a_mid_deg'))}")
        lines.append("")
        lines.append(f"B start: {self._fmt(m.get('b_start_deg'))}")
        lines.append(f"B end:   {self._fmt(m.get('b_end_deg'))}")
        lines.append(f"B dur.:  {self._fmt(m.get('b_open_total_deg'))}")
        lines.append(f"B mid:   {self._fmt(m.get('b_mid_deg'))}")

        if "overlap_total_deg" in m:
            lines.append("")
            lines.append(f"Overlap start: {self._fmt(m.get('overlap_start_deg'))}")
            lines.append(f"Overlap end:   {self._fmt(m.get('overlap_end_deg'))}")
            lines.append(f"Overlap dur.:  {self._fmt(m.get('overlap_total_deg'))}")
            lines.append(f"Overlap mid:   {self._fmt(m.get('overlap_mid_deg'))}")

        if "blowdown_total_deg" in m:
            lines.append("")
            lines.append(f"Blowdown start: {self._fmt(m.get('blowdown_start_deg'))}")
            lines.append(f"Blowdown end:   {self._fmt(m.get('blowdown_end_deg'))}")
            lines.append(f"Blowdown dur.:  {self._fmt(m.get('blowdown_total_deg'))}")
            lines.append(f"Blowdown mid:   {self._fmt(m.get('blowdown_mid_deg'))}")

        if "scavenge_total_deg" in m:
            lines.append("")
            lines.append(f"Scavenge start: {self._fmt(m.get('scavenge_start_deg'))}")
            lines.append(f"Scavenge end:   {self._fmt(m.get('scavenge_end_deg'))}")
            lines.append(f"Scavenge dur.:  {self._fmt(m.get('scavenge_total_deg'))}")
            lines.append(f"Scavenge mid:   {self._fmt(m.get('scavenge_mid_deg'))}")

        p.setPen(QPen(fg, 1))
        p.drawText(metrics_rect.adjusted(12, 30, -12, -12), Qt.AlignLeft | Qt.AlignTop, "\n".join(lines))


class ProjectStructureDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Project structure", parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.setWidget(self.tree)

    def rebuild(self, cfg: dict):
        self.tree.clear()

        root = QTreeWidgetItem(["Configuration"])
        self.tree.addTopLevelItem(root)

        def add(parent, name, value):
            node = QTreeWidgetItem([name])
            parent.addChild(node)
            if isinstance(value, dict):
                for k, v in value.items():
                    add(node, k, v)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    add(node, f"[{i}]", v)

        for key, val in cfg.items():
            add(root, key, val)

        self.tree.expandToDepth(2)


class PropertyInspectorTab(BasicTab):
    def __init__(self):
        super().__init__("Property inspector")
        self.sections: list[CollapsibleSection] = []

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search properties, tabs, names, fields…")
        self.btn_expand = QPushButton("Expand all")
        self.btn_collapse = QPushButton("Collapse all")
        self.btn_sync = QPushButton("Sync from current config")
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_expand)
        top.addWidget(self.btn_collapse)
        top.addWidget(self.btn_sync)
        self.layout.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_host = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_host)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_host)
        self.layout.addWidget(self.scroll, 1)

        self.search.textChanged.connect(self.apply_filter)
        self.btn_expand.clicked.connect(self.expand_all)
        self.btn_collapse.clicked.connect(self.collapse_all)

    def rebuild(self, cfg: dict) -> None:
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.sections.clear()

        def add_section(title: str, data):
            sec = CollapsibleSection(title)
            form = QFormLayout()
            form.setContentsMargins(0, 0, 0, 0)
            form.setSpacing(6)
            self._fill_form(form, data)
            sec.body_layout.addLayout(form)
            self.scroll_layout.addWidget(sec)
            self.sections.append(sec)

        add_section("Engine", cfg.get("engine", {}))
        add_section("Gas", cfg.get("gas", {}))
        add_section("Simulation", cfg.get("simulation", {}))
        add_section("Gas exchange", cfg.get("gasexchange", {}))
        add_section("Plena", cfg.get("plena", {}))
        add_section("Throttle", cfg.get("throttle", {}))
        add_section("Output/Postprocess", {
            "output_files": cfg.get("output_files", {}),
            "postprocess": cfg.get("postprocess", {}),
        })
        for i, cyl in enumerate(cfg.get("user_cylinders", []), start=1):
            add_section(f"User cylinder {i}: {cyl.get('name', f'cyl_{i}')}", cyl)

        self.scroll_layout.addStretch(1)
        self.apply_filter(self.search.text())

    def _fill_form(self, form: QFormLayout, data, prefix: str = "") -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                label = f"{prefix}{key}"
                if isinstance(value, dict):
                    sub = QLabel(f"<b>{label}</b>")
                    form.addRow(sub)
                    self._fill_form(form, value, prefix=f"{label}.")
                elif isinstance(value, list):
                    form.addRow(QLabel(f"{label}"), QLabel(f"list[{len(value)}]"))
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            sub = QLabel(f"<i>{label}[{i}]</i>")
                            form.addRow(sub)
                            self._fill_form(form, item, prefix=f"{label}[{i}].")
                        else:
                            form.addRow(QLabel(f"{label}[{i}]"), QLabel(str(item)))
                else:
                    value_lab = QLabel(str(value))
                    value_lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    form.addRow(QLabel(label), value_lab)
        else:
            form.addRow(QLabel(prefix.rstrip(".")), QLabel(str(data)))

    def apply_filter(self, text: str) -> None:
        for sec in self.sections:
            sec.setVisible(sec.matches(text))

    def expand_all(self):
        for sec in self.sections:
            if not sec._expanded:
                sec.toggle_expanded()

    def collapse_all(self):
        for sec in self.sections:
            if sec._expanded:
                sec.toggle_expanded()


class OverviewTab(BasicTab):
    def __init__(self):
        super().__init__("Overview / Quick access")
        self._jump_callback = None

        top = QGridLayout()

        self.lbl_case = QLabel("Case: -")
        self.lbl_cycle = QLabel("Cycle: -")
        self.lbl_speed = QLabel("Speed: -")
        self.lbl_gx = QLabel("Gas exchange: -")
        self.lbl_cyl = QLabel("Cylinders: -")
        self.lbl_throttle = QLabel("Throttle: -")
        self.lbl_plena = QLabel("Plena: -")
        self.lbl_output = QLabel("Output: -")

        labels = [
            self.lbl_case, self.lbl_cycle, self.lbl_speed, self.lbl_gx,
            self.lbl_cyl, self.lbl_throttle, self.lbl_plena, self.lbl_output
        ]
        for i, lab in enumerate(labels):
            lab.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 8px; border: 1px solid #d8e0ee; border-radius: 10px;")
            top.addWidget(lab, i // 2, i % 2)

        self.layout.addLayout(top)

        quick = QGroupBox("Quick navigation")
        ql = QHBoxLayout(quick)
        self.btn_inspector = QPushButton("Inspector")
        self.btn_engine = QPushButton("Engine")
        self.btn_gx = QPushButton("Gas exchange")
        self.btn_uc = QPushButton("User cylinder")
        self.btn_plena = QPushButton("Plena")
        self.btn_throttle = QPushButton("Throttle")
        self.btn_timing = QPushButton("Timing")
        self.btn_results = QPushButton("Run/Results")
        for b in [self.btn_inspector, self.btn_engine, self.btn_gx, self.btn_uc, self.btn_plena, self.btn_throttle, self.btn_timing, self.btn_results]:
            ql.addWidget(b)
        self.layout.addWidget(quick)

        diag = QGroupBox("Validation / diagnostics")
        dl = QVBoxLayout(diag)
        self.validation_label = QLabel("No validation yet.")
        self.validation_label.setStyleSheet("font-weight: 700;")
        self.validation_text = QPlainTextEdit()
        self.validation_text.setReadOnly(True)
        self.validation_text.setMinimumHeight(280)
        dl.addWidget(self.validation_label)
        dl.addWidget(self.validation_text)
        self.layout.addWidget(diag, 1)

    def set_jump_callback(self, callback) -> None:
        self._jump_callback = callback
        self.btn_inspector.clicked.connect(lambda: self._jump_callback("Inspector"))
        self.btn_engine.clicked.connect(lambda: self._jump_callback("Engine"))
        self.btn_gx.clicked.connect(lambda: self._jump_callback("Gas exchange"))
        self.btn_uc.clicked.connect(lambda: self._jump_callback("User cylinder"))
        self.btn_plena.clicked.connect(lambda: self._jump_callback("Plena"))
        self.btn_throttle.clicked.connect(lambda: self._jump_callback("Throttle"))
        self.btn_timing.clicked.connect(lambda: self._jump_callback("Gas exchange"))
        self.btn_results.clicked.connect(lambda: self._jump_callback("Run/Results"))

    def update_summary(self, cfg: dict, diagnostics: dict | None = None) -> None:
        eng = cfg.get("engine", {})
        gx = cfg.get("gasexchange", {})
        cyls = cfg.get("user_cylinders", [])
        enabled = [c for c in cyls if c.get("enabled", True)]
        throttle = cfg.get("throttle", {})
        plena = cfg.get("plena", {})
        out = cfg.get("output_files", {})

        self.lbl_case.setText(f"Case: {cfg.get('case_name', '-')}")
        self.lbl_cycle.setText(f"Cycle: {eng.get('cycle_type', '-')} | CR: {eng.get('compression_ratio', '-')}")
        speed_txt = f"RPM: {eng.get('rpm', '-')}"
        if eng.get("freq_hz", 0):
            speed_txt += f" | f: {eng.get('freq_hz')}"
        self.lbl_speed.setText(speed_txt)
        self.lbl_gx.setText(f"Gas exchange: {gx.get('mode', '-')} | Flow: {gx.get('flow_model', '-')}")
        self.lbl_cyl.setText(f"Cylinders: {len(enabled)}/{len(cyls)} enabled | active={cfg.get('active_user_cylinder', '-')}")
        self.lbl_throttle.setText(f"Throttle: {'on' if throttle.get('enabled', False) else 'off'} | pos={throttle.get('position', '-')}")
        self.lbl_plena.setText(f"Plena: {'on' if plena.get('enabled', False) else 'off'} | Vin={plena.get('intake',{}).get('volume_m3','-')} m³")
        self.lbl_output.setText(f"Output: {out.get('out_dir', '-')} | {out.get('csv_name', '-')}")

        if diagnostics is None:
            self.validation_label.setText("Validation / diagnostics")
            return

        errs = diagnostics.get("errors", [])
        warns = diagnostics.get("warnings", [])
        infos = diagnostics.get("info", [])
        self.validation_label.setText(f"Validation: {len(errs)} error(s), {len(warns)} warning(s), {len(infos)} info")
        lines = []
        if errs:
            lines.append("Errors:")
            lines.extend([f"  - {x}" for x in errs])
        if warns:
            lines.append("")
            lines.append("Warnings:")
            lines.extend([f"  - {x}" for x in warns])
        if infos:
            lines.append("")
            lines.append("Info:")
            lines.extend([f"  - {x}" for x in infos])
        self.validation_text.setPlainText("\n".join(lines).strip())


class EngineTab(BasicTab):
    def __init__(self):
        super().__init__("Engine")
        form = QFormLayout()
        self.case_name = ConfigFieldFactory.line()
        self.cycle_type = ConfigFieldFactory.combo(["2T", "4T"], "4T")
        self.rpm = ConfigFieldFactory.dspin(3000.0, 0.0, 100000.0, 100.0, 3)
        self.freq_hz = ConfigFieldFactory.dspin(0.0, 0.0, 100000.0, 1.0, 3)
        self.bore = ConfigFieldFactory.dspin(0.086, 0.0, 10.0, 0.001, 6)
        self.stroke = ConfigFieldFactory.dspin(0.086, 0.0, 10.0, 0.001, 6)
        self.conrod = ConfigFieldFactory.dspin(0.143, 0.0, 10.0, 0.001, 6)
        self.cr = ConfigFieldFactory.dspin(10.5, 1.0, 100.0, 0.1, 4)
        form.addRow("Case name", self.case_name)
        form.addRow("Cycle type", self.cycle_type)
        form.addRow("RPM", self.rpm)
        form.addRow("Frequency [Hz] (optional)", self.freq_hz)
        form.addRow("Bore [m]", self.bore)
        form.addRow("Stroke [m]", self.stroke)
        form.addRow("Conrod [m]", self.conrod)
        form.addRow("Compression ratio [-]", self.cr)
        self.layout.addLayout(form)

    def all_widgets(self):
        return [self.case_name, self.cycle_type, self.rpm, self.freq_hz, self.bore, self.stroke, self.conrod, self.cr]


    def set_assembly_callback(self, callback) -> None:
        self._assembly_callback = callback

    def _emit_update(self, *args) -> None:
        if self._assembly_callback is not None:
            self._assembly_callback()

    def set_config(self, cfg: dict) -> None:
        self.case_name.setText(str(cfg.get("case_name", "")))
        engine = cfg["engine"]
        self.cycle_type.setCurrentText(str(engine.get("cycle_type", "4T")))
        self.rpm.setValue(float(engine.get("rpm") or 0.0))
        self.freq_hz.setValue(float(engine.get("freq_hz") or 0.0))
        self.bore.setValue(float(engine.get("bore_m", 0.086)))
        self.stroke.setValue(float(engine.get("stroke_m", 0.086)))
        self.conrod.setValue(float(engine.get("conrod_m", 0.143)))
        self.cr.setValue(float(engine.get("compression_ratio", 10.5)))

    def update_config(self, cfg: dict) -> None:
        cfg["case_name"] = self.case_name.text().strip()
        cfg["engine"] = {
            "cycle_type": self.cycle_type.currentText(),
            "rpm": float(self.rpm.value()) if self.rpm.value() > 0.0 else None,
            "freq_hz": float(self.freq_hz.value()) if self.freq_hz.value() > 0.0 else None,
            "bore_m": float(self.bore.value()),
            "stroke_m": float(self.stroke.value()),
            "conrod_m": float(self.conrod.value()),
            "compression_ratio": float(self.cr.value()),
        }


class GasTab(BasicTab):
    def __init__(self):
        super().__init__("Gas / Initial / Manifolds")
        grid = QGridLayout()

        self.R = ConfigFieldFactory.dspin(287.0, 1.0, 1e6, 1.0, 6)
        self.cp = ConfigFieldFactory.dspin(1005.0, 1.0, 1e7, 1.0, 6)
        self.p0 = ConfigFieldFactory.dspin(100000.0, 0.0, 1e9, 1000.0, 3)
        self.T0 = ConfigFieldFactory.dspin(300.0, 0.0, 5000.0, 1.0, 3)
        self.p_int = ConfigFieldFactory.dspin(100000.0, 0.0, 1e9, 1000.0, 3)
        self.T_int = ConfigFieldFactory.dspin(300.0, 0.0, 5000.0, 1.0, 3)
        self.p_ex = ConfigFieldFactory.dspin(105000.0, 0.0, 1e9, 1000.0, 3)
        self.T_ex = ConfigFieldFactory.dspin(650.0, 0.0, 5000.0, 1.0, 3)

        box1 = QGroupBox("Gas")
        f1 = QFormLayout(box1)
        f1.addRow("R [J/kg/K]", self.R)
        f1.addRow("cp [J/kg/K]", self.cp)

        box2 = QGroupBox("Initial cylinder state")
        f2 = QFormLayout(box2)
        f2.addRow("p0 [Pa]", self.p0)
        f2.addRow("T0 [K]", self.T0)

        box3 = QGroupBox("Manifolds")
        f3 = QFormLayout(box3)
        f3.addRow("Intake p [Pa]", self.p_int)
        f3.addRow("Intake T [K]", self.T_int)
        f3.addRow("Exhaust p [Pa]", self.p_ex)
        f3.addRow("Exhaust T [K]", self.T_ex)

        grid.addWidget(box1, 0, 0)
        grid.addWidget(box2, 0, 1)
        grid.addWidget(box3, 1, 0, 1, 2)
        self.layout.addLayout(grid)

    def set_config(self, cfg: dict) -> None:
        gas = cfg["gas"]
        init = cfg["initial"]
        man = cfg["manifolds"]
        self.R.setValue(float(gas.get("R_J_per_kgK", 287.0)))
        self.cp.setValue(float(gas.get("cp_J_per_kgK", 1005.0)))
        self.p0.setValue(float(init.get("p0_pa", 100000.0)))
        self.T0.setValue(float(init.get("T0_K", 300.0)))
        self.p_int.setValue(float(man.get("p_int_pa", 100000.0)))
        self.T_int.setValue(float(man.get("T_int_K", 300.0)))
        self.p_ex.setValue(float(man.get("p_ex_pa", 105000.0)))
        self.T_ex.setValue(float(man.get("T_ex_K", 650.0)))

    def update_config(self, cfg: dict) -> None:
        cfg["gas"] = {
            "R_J_per_kgK": float(self.R.value()),
            "cp_J_per_kgK": float(self.cp.value()),
        }
        cfg["initial"] = {
            "p0_pa": float(self.p0.value()),
            "T0_K": float(self.T0.value()),
        }
        cfg["manifolds"] = {
            "p_int_pa": float(self.p_int.value()),
            "T_int_K": float(self.T_int.value()),
            "p_ex_pa": float(self.p_ex.value()),
            "T_ex_K": float(self.T_ex.value()),
        }


class SimulationTab(BasicTab):
    def __init__(self):
        super().__init__("Simulation")
        grid = QGridLayout()
        self.t0 = ConfigFieldFactory.dspin(0.0, -1e6, 1e6, 0.001, 6)
        self.theta0 = ConfigFieldFactory.dspin(0.0, -1e6, 1e6, 1.0, 6)
        self.n_cycles = ConfigFieldFactory.ispin(1, 1, 100000, 1)
        self.int_type = ConfigFieldFactory.combo(["rk4_fixed", "scipy"], "rk4_fixed")
        self.method = ConfigFieldFactory.line("RK45")
        self.rtol = ConfigFieldFactory.dspin(1e-8, 0.0, 1.0, 1e-8, 12)
        self.atol = ConfigFieldFactory.dspin(1e-10, 0.0, 1.0, 1e-10, 12)
        self.max_step = ConfigFieldFactory.dspin(1e-4, 0.0, 1.0, 1e-5, 8)
        self.dt_internal = ConfigFieldFactory.dspin(1e-5, 0.0, 1.0, 1e-6, 8)
        self.dt_out = ConfigFieldFactory.dspin(1e-4, 0.0, 1.0, 1e-5, 8)
        self.dtheta_out = ConfigFieldFactory.dspin(0.5, 0.0, 1000.0, 0.1, 4)
        self.live_enabled = ConfigFieldFactory.check(False)
        self.every_n = ConfigFieldFactory.ispin(5, 1, 100000, 1)
        self.window_s = ConfigFieldFactory.dspin(0.02, 0.0, 1000.0, 0.01, 6)

        a = QGroupBox("Time / cycle")
        fa = QFormLayout(a)
        fa.addRow("t0 [s]", self.t0)
        fa.addRow("theta0 [deg]", self.theta0)
        fa.addRow("n_cycles", self.n_cycles)

        b = QGroupBox("Integrator")
        fb = QFormLayout(b)
        fb.addRow("Type", self.int_type)
        fb.addRow("Method", self.method)
        fb.addRow("rtol", self.rtol)
        fb.addRow("atol", self.atol)
        fb.addRow("max_step [s]", self.max_step)
        fb.addRow("dt_internal [s]", self.dt_internal)

        c = QGroupBox("Output / live plot")
        fc = QFormLayout(c)
        fc.addRow("dt_out [s]", self.dt_out)
        fc.addRow("dtheta_out [deg]", self.dtheta_out)
        fc.addRow("Live plot enabled", self.live_enabled)
        fc.addRow("Live every_n_out", self.every_n)
        fc.addRow("Live window [s]", self.window_s)

        grid.addWidget(a, 0, 0)
        grid.addWidget(b, 0, 1)
        grid.addWidget(c, 1, 0, 1, 2)
        self.layout.addLayout(grid)

    def set_config(self, cfg: dict) -> None:
        sim = cfg["simulation"]
        it = sim["integrator"]
        out = sim["output"]
        lp = sim["live_plot"]
        self.t0.setValue(float(sim.get("t0_s", 0.0)))
        self.theta0.setValue(float(sim.get("theta0_deg", 0.0)))
        self.n_cycles.setValue(int(sim.get("n_cycles", 1)))
        self.int_type.setCurrentText(str(it.get("type", "rk4_fixed")))
        self.method.setText(str(it.get("method", "RK45")))
        self.rtol.setValue(float(it.get("rtol", 1e-8)))
        self.atol.setValue(float(it.get("atol", 1e-10)))
        self.max_step.setValue(float(it.get("max_step_s", 1e-4)))
        self.dt_internal.setValue(float(it.get("dt_internal_s", 1e-5)))
        self.dt_out.setValue(float(out.get("dt_out_s", 1e-4)))
        self.dtheta_out.setValue(float(out.get("dtheta_out_deg", 0.5)))
        self.live_enabled.setChecked(bool(lp.get("enabled", False)))
        self.every_n.setValue(int(lp.get("every_n_out", 5)))
        self.window_s.setValue(float(lp.get("window_s", 0.02)))

    def update_config(self, cfg: dict) -> None:
        cfg["simulation"] = {
            "t0_s": float(self.t0.value()),
            "theta0_deg": float(self.theta0.value()),
            "n_cycles": int(self.n_cycles.value()),
            "integrator": {
                "type": self.int_type.currentText(),
                "method": self.method.text().strip(),
                "rtol": float(self.rtol.value()),
                "atol": float(self.atol.value()),
                "max_step_s": float(self.max_step.value()),
                "dt_internal_s": float(self.dt_internal.value()),
            },
            "output": {
                "dt_out_s": float(self.dt_out.value()),
                "dtheta_out_deg": float(self.dtheta_out.value()),
            },
            "live_plot": {
                "enabled": bool(self.live_enabled.isChecked()),
                "every_n_out": int(self.every_n.value()),
                "window_s": float(self.window_s.value()),
            },
        }


class ValvesTab(BasicTab):
    def __init__(self):
        super().__init__("Valves")
        self._preview_callback = None
        self.preview = ValvePreviewWidget()

        self.int_ref = ConfigFieldFactory.dspin(360.0, -1e6, 1e6, 1.0, 3)
        self.int_mode = ConfigFieldFactory.combo(["BTDC", "ATDC", "BBDC", "ABDC"], "BTDC")
        self.int_deg = ConfigFieldFactory.dspin(10.0, -1e6, 1e6, 1.0, 3)
        self.int_align = ConfigFieldFactory.combo(["open", "close"], "open")

        self.ex_ref = ConfigFieldFactory.dspin(180.0, -1e6, 1e6, 1.0, 3)
        self.ex_mode = ConfigFieldFactory.combo(["BTDC", "ATDC", "BBDC", "ABDC"], "BBDC")
        self.ex_deg = ConfigFieldFactory.dspin(40.0, -1e6, 1e6, 1.0, 3)
        self.ex_align = ConfigFieldFactory.combo(["open", "close"], "open")

        self.lift_file = ConfigFieldFactory.file_line(dialog_title="Ventilhubkurve auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)")
        self.ak_file = ConfigFieldFactory.file_line(dialog_title="alphaK-Datei auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)")
        self.d_in = ConfigFieldFactory.dspin(0.032, 0.0, 1.0, 0.001, 6)
        self.d_ex = ConfigFieldFactory.dspin(0.028, 0.0, 1.0, 0.001, 6)
        self.count_in = ConfigFieldFactory.spin(2, 1, 32, 1)
        self.count_ex = ConfigFieldFactory.spin(2, 1, 32, 1)
        self.A_in = ConfigFieldFactory.dspin(8e-4, 0.0, 10.0, 1e-4, 8)
        self.A_ex = ConfigFieldFactory.dspin(7e-4, 0.0, 10.0, 1e-4, 8)
        self.in_angle_scale = ConfigFieldFactory.dspin(1.0, 0.0, 1000.0, 0.01, 6)
        self.in_lift_scale = ConfigFieldFactory.dspin(1.0, 0.0, 1000.0, 0.01, 6)
        self.ex_angle_scale = ConfigFieldFactory.dspin(1.0, 0.0, 1000.0, 0.01, 6)
        self.ex_lift_scale = ConfigFieldFactory.dspin(1.0, 0.0, 1000.0, 0.01, 6)
        self.lift_basis = ConfigFieldFactory.combo(["crank", "cam"], "crank")
        self.cam_ratio = ConfigFieldFactory.dspin(2.0, 0.0, 1000.0, 0.1, 6)
        self.eff_lift_thr = ConfigFieldFactory.dspin(0.1, 0.0, 100.0, 0.01, 6)
        self.btn_refresh_preview = QPushButton("Update valve preview")

        grid = QGridLayout()
        a = QGroupBox("Files / dimensions")
        fa = QFormLayout(a)
        fa.addRow("Lift file", self.lift_file)
        fa.addRow("alphaK file (x=Hub, y1/y2=alphaK bezogen auf A_piston)", self.ak_file)
        fa.addRow("d_in [m]", self.d_in)
        fa.addRow("d_ex [m]", self.d_ex)
        fa.addRow("count_in [-]", self.count_in)
        fa.addRow("count_ex [-]", self.count_ex)
        fa.addRow("A_in_max [m²]", self.A_in)
        fa.addRow("A_ex_max [m²]", self.A_ex)

        b = QGroupBox("Intake timing")
        fb = QFormLayout(b)
        fb.addRow("ref_deg", self.int_ref)
        fb.addRow("mode", self.int_mode)
        fb.addRow("deg", self.int_deg)
        fb.addRow("align", self.int_align)

        c = QGroupBox("Exhaust timing")
        fc = QFormLayout(c)
        fc.addRow("ref_deg", self.ex_ref)
        fc.addRow("mode", self.ex_mode)
        fc.addRow("deg", self.ex_deg)
        fc.addRow("align", self.ex_align)

        d = QGroupBox("Scaling / basis")
        fd = QFormLayout(d)
        fd.addRow("int angle_scale", self.in_angle_scale)
        fd.addRow("int lift_scale", self.in_lift_scale)
        fd.addRow("ex angle_scale", self.ex_angle_scale)
        fd.addRow("ex lift_scale", self.ex_lift_scale)
        fd.addRow("lift angle basis", self.lift_basis)
        fd.addRow("cam_to_crank_ratio", self.cam_ratio)
        fd.addRow("effective_lift_threshold_mm", self.eff_lift_thr)
        fd.addRow("", self.btn_refresh_preview)

        grid.addWidget(a, 0, 0)
        grid.addWidget(b, 0, 1)
        grid.addWidget(c, 1, 0)
        grid.addWidget(d, 1, 1)
        self.layout.addLayout(grid)
        self.layout.addWidget(self.preview)

        self.btn_refresh_preview.clicked.connect(self._trigger_preview)
        for w in self.preview_widgets():
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._trigger_preview)
            elif hasattr(w, "currentTextChanged"):
                w.currentTextChanged.connect(self._trigger_preview)
            elif hasattr(w, "textChanged"):
                w.textChanged.connect(self._trigger_preview)

    def preview_widgets(self):
        return [
            self.int_ref, self.int_mode, self.int_deg, self.int_align,
            self.ex_ref, self.ex_mode, self.ex_deg, self.ex_align,
            self.lift_file, self.ak_file, self.d_in, self.d_ex, self.count_in, self.count_ex, self.A_in, self.A_ex,
            self.in_angle_scale, self.in_lift_scale, self.ex_angle_scale, self.ex_lift_scale,
            self.lift_basis, self.cam_ratio, self.eff_lift_thr
        ]

    def _browse_table_path(self, table: QTableWidget, row: int, col: int) -> None:
        if col != 8 or row < 0:
            return
        current = _item_text(table, row, col, "")
        start_dir = str(Path(current).expanduser().parent) if current else str(Path.cwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "alphaK-Datei auswählen",
            start_dir,
            "Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)",
        )
        if path:
            table.blockSignals(True)
            _set_table_item(table, row, col, path)
            table.blockSignals(False)
            self._update_sketch()
            self._trigger_preview()

    def set_preview_callback(self, callback) -> None:
        self._preview_callback = callback

    def _trigger_preview(self, *args) -> None:
        if self._preview_callback is not None:
            self._preview_callback()

    def set_config(self, cfg: dict) -> None:
        v = cfg["gasexchange"]["valves"]
        self.lift_file.setText(str(v.get("lift_file", "")))
        self.ak_file.setText(str(v.get("alphak_file", "")))
        self.d_in.setValue(float(v.get("d_in_m", 0.032)))
        self.d_ex.setValue(float(v.get("d_ex_m", 0.028)))
        self.count_in.setValue(int(v.get("count_in", 2)))
        self.count_ex.setValue(int(v.get("count_ex", 2)))
        self.A_in.setValue(float(v.get("A_in_port_max_m2", 8e-4)))
        self.A_ex.setValue(float(v.get("A_ex_port_max_m2", 7e-4)))
        io = v.get("intake_open", {})
        eo = v.get("exhaust_open", {})
        self.int_ref.setValue(float(io.get("ref_deg", 360.0)))
        self.int_mode.setCurrentText(str(io.get("mode", "BTDC")))
        self.int_deg.setValue(float(io.get("deg", 10.0)))
        self.int_align.setCurrentText(str(io.get("align", "open")))
        self.ex_ref.setValue(float(eo.get("ref_deg", 180.0)))
        self.ex_mode.setCurrentText(str(eo.get("mode", "BBDC")))
        self.ex_deg.setValue(float(eo.get("deg", 40.0)))
        self.ex_align.setCurrentText(str(eo.get("align", "open")))
        sc = v.get("scaling", {})
        si = sc.get("intake", {})
        se = sc.get("exhaust", {})
        self.in_angle_scale.setValue(float(si.get("angle_scale", 1.0)))
        self.in_lift_scale.setValue(float(si.get("lift_scale", 1.0)))
        self.ex_angle_scale.setValue(float(se.get("angle_scale", 1.0)))
        self.ex_lift_scale.setValue(float(se.get("lift_scale", 1.0)))
        self.lift_basis.setCurrentText(str(v.get("lift_angle_basis", "crank")))
        self.cam_ratio.setValue(float(v.get("cam_to_crank_ratio", 2.0)))
        self.eff_lift_thr.setValue(float(v.get("effective_lift_threshold_mm", 0.1)))
        self._trigger_preview()

    def update_config(self, cfg: dict) -> None:
        cfg["gasexchange"]["valves"] = {
            "lift_file": self.lift_file.text().strip(),
            "alphak_file": self.ak_file.text().strip(),
            "d_in_m": float(self.d_in.value()),
            "d_ex_m": float(self.d_ex.value()),
            "count_in": int(self.count_in.value()),
            "count_ex": int(self.count_ex.value()),
            "A_in_port_max_m2": float(self.A_in.value()),
            "A_ex_port_max_m2": float(self.A_ex.value()),
            "intake_open": {
                "ref_deg": float(self.int_ref.value()),
                "mode": self.int_mode.currentText(),
                "deg": float(self.int_deg.value()),
                "align": self.int_align.currentText(),
            },
            "exhaust_open": {
                "ref_deg": float(self.ex_ref.value()),
                "mode": self.ex_mode.currentText(),
                "deg": float(self.ex_deg.value()),
                "align": self.ex_align.currentText(),
            },
            "scaling": {
                "intake": {
                    "angle_scale": float(self.in_angle_scale.value()),
                    "lift_scale": float(self.in_lift_scale.value()),
                },
                "exhaust": {
                    "angle_scale": float(self.ex_angle_scale.value()),
                    "lift_scale": float(self.ex_lift_scale.value()),
                },
            },
            "lift_angle_basis": self.lift_basis.currentText(),
            "cam_to_crank_ratio": float(self.cam_ratio.value()),
            "effective_lift_threshold_mm": float(self.eff_lift_thr.value()),
        }


class PortsTab(BasicTab):
    def __init__(self):
        super().__init__("Ports")
        form = QFormLayout()
        self.area_file = ConfigFieldFactory.file_line(dialog_title="Portflächen-Datei auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)")
        self.ak_file = ConfigFieldFactory.file_line(dialog_title="alphaK-Datei auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)")
        form.addRow("Area file", self.area_file)
        form.addRow("alphaK file (x=Hub, y1/y2=alphaK bezogen auf A_piston)", self.ak_file)
        self.layout.addLayout(form)

    def set_config(self, cfg: dict) -> None:
        p = cfg["gasexchange"]["ports"]
        self.area_file.setText(str(p.get("area_file", "")))
        self.ak_file.setText(str(p.get("alphak_file", "")))

    def update_config(self, cfg: dict) -> None:
        cfg["gasexchange"]["ports"] = {"area_file": self.area_file.text().strip(), "alphak_file": self.ak_file.text().strip()}


class SlotsTab(BasicTab):
    COLUMNS = [
        "width_m", "height_m", "count", "offset_from_ut_m",
        "roof_type", "roof_len_m", "roof_angle_deg", "roof_gamma",
        "alphak_file", "zeta_local", "friction_factor", "length_m", "hydraulic_diameter_m", "phi_min"
    ]

    def __init__(self):
        super().__init__("Slots")
        self._preview_callback = None
        self.default_ak_file = ConfigFieldFactory.file_line(dialog_title="Standard-alphaK-Datei auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)")
        self.single_intake = self._make_single_group_box("Single intake")
        self.single_exhaust = self._make_single_group_box("Single exhaust")
        self.intake_table = self._make_group_table()
        self.exhaust_table = self._make_group_table()
        self.sketch = SlotSketchWidget()
        self.preview = ValvePreviewWidget()

        top = QFormLayout()
        top.addRow("Default slot alphaK file", self.default_ak_file)
        self.layout.addLayout(top)

        singles = QGridLayout()
        singles.addWidget(self.single_intake["box"], 0, 0)
        singles.addWidget(self.single_exhaust["box"], 0, 1)
        self.layout.addLayout(singles)

        btn_row = QHBoxLayout()
        self.btn_add_int = QPushButton("Add intake group")
        self.btn_add_ex = QPushButton("Add exhaust group")
        self.btn_del_int = QPushButton("Delete intake group")
        self.btn_del_ex = QPushButton("Delete exhaust group")
        for b in (self.btn_add_int, self.btn_add_ex, self.btn_del_int, self.btn_del_ex):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        self.layout.addLayout(btn_row)

        split = QSplitter(Qt.Horizontal)
        self._outer_splitter = split
        split.setChildrenCollapsible(False)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Intake groups"))
        ll.addWidget(self.intake_table)
        right = QWidget()
        rr = QVBoxLayout(right)
        rr.addWidget(QLabel("Exhaust groups"))
        rr.addWidget(self.exhaust_table)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([600, 600])
        self.layout.addWidget(split)
        self.layout.addWidget(self.sketch)
        self.layout.addWidget(self.preview)

        self.btn_add_int.clicked.connect(lambda: self._append_row(self.intake_table))
        self.btn_add_ex.clicked.connect(lambda: self._append_row(self.exhaust_table))
        self.btn_del_int.clicked.connect(lambda: self._delete_selected(self.intake_table))
        self.btn_del_ex.clicked.connect(lambda: self._delete_selected(self.exhaust_table))
        self.intake_table.itemChanged.connect(self._update_sketch)
        self.exhaust_table.itemChanged.connect(self._update_sketch)
        self.intake_table.cellDoubleClicked.connect(lambda row, col: self._browse_table_path(self.intake_table, row, col))
        self.exhaust_table.cellDoubleClicked.connect(lambda row, col: self._browse_table_path(self.exhaust_table, row, col))
        self.default_ak_file.textChanged.connect(self._trigger_preview)


    def _browse_table_path(self, table: QTableWidget, row: int, col: int) -> None:
        if col != 8 or row < 0:
            return
        current = _item_text(table, row, col, "")
        start_dir = str(Path(current).expanduser().parent) if current else str(Path.cwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "alphaK-Datei auswählen",
            start_dir,
            "Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)",
        )
        if path:
            table.blockSignals(True)
            _set_table_item(table, row, col, path)
            table.blockSignals(False)
            self._update_sketch()
            self._trigger_preview()

    def set_preview_callback(self, callback) -> None:
        self._preview_callback = callback

    def _trigger_preview(self, *args) -> None:
        if self._preview_callback is not None:
            self._preview_callback()

    def _make_group_table(self) -> QTableWidget:
        t = QTableWidget(0, len(self.COLUMNS))
        t.setHorizontalHeaderLabels(self.COLUMNS)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setAlternatingRowColors(True)
        return t

    def _append_row(self, table: QTableWidget, group: dict | None = None) -> None:
        row = table.rowCount()
        table.insertRow(row)
        group = group or {}
        roof = group.get("roof", {}) or {}
        channel = group.get("channel", {}) or {}
        vals = [
            group.get("width_m", 0.01), group.get("height_m", 0.02), group.get("count", 1), group.get("offset_from_ut_m", 0.0),
            roof.get("type", "none"), roof.get("len_m", ""), roof.get("angle_deg", ""), roof.get("gamma", ""),
            group.get("alphak_file", ""), channel.get("zeta_local", ""), channel.get("friction_factor", ""),
            channel.get("length_m", ""), channel.get("hydraulic_diameter_m", ""), channel.get("phi_min", ""),
        ]
        for c, v in enumerate(vals):
            _set_table_item(table, row, c, v)
        self._update_sketch()
        self._trigger_preview()
        self._trigger_preview()

    def _delete_selected(self, table: QTableWidget) -> None:
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for r in rows:
            table.removeRow(r)
        self._update_sketch()
        self._trigger_preview()

    def _make_single_group_box(self, title: str) -> dict:
        box = QGroupBox(title)
        form = QFormLayout(box)
        d = {
            "width_m": ConfigFieldFactory.dspin(0.01, 0.0, 1.0, 0.001, 6),
            "height_m": ConfigFieldFactory.dspin(0.02, 0.0, 1.0, 0.001, 6),
            "count": ConfigFieldFactory.ispin(1, 0, 10000, 1),
            "offset_from_ut_m": ConfigFieldFactory.dspin(0.015, 0.0, 1.0, 0.001, 6),
            "roof_type": ConfigFieldFactory.combo(["none", "linear", "cos", "factor", "angle"], "cos"),
            "roof_len_m": ConfigFieldFactory.dspin(0.004, 0.0, 1.0, 0.001, 6),
            "roof_angle_deg": ConfigFieldFactory.dspin(20.0, 0.0, 89.9, 1.0, 4),
            "roof_gamma": ConfigFieldFactory.dspin(1.0, 0.0, 100.0, 0.1, 4),
            "alphak_file": ConfigFieldFactory.file_line(dialog_title=f"alphaK-Datei für {title} auswählen", file_filter="Kurvendateien (*.csv *.txt *.dat);;CSV (*.csv);;Textdateien (*.txt *.dat);;Alle Dateien (*)"),
            "zeta_local": ConfigFieldFactory.dspin(1.0, 0.0, 1000.0, 0.1, 6),
            "friction_factor": ConfigFieldFactory.dspin(0.02, 0.0, 10.0, 0.01, 6),
            "length_m": ConfigFieldFactory.dspin(0.03, 0.0, 100.0, 0.001, 6),
            "hydraulic_diameter_m": ConfigFieldFactory.dspin(0.01, 0.0, 100.0, 0.001, 6),
            "phi_min": ConfigFieldFactory.dspin(0.2, 0.0, 1.0, 0.01, 4),
            "box": box,
        }
        form.addRow("width_m", d["width_m"]); form.addRow("height_m", d["height_m"]); form.addRow("count", d["count"])
        form.addRow("offset_from_ut_m", d["offset_from_ut_m"]); form.addRow("roof_type", d["roof_type"])
        form.addRow("roof_len_m", d["roof_len_m"]); form.addRow("roof_angle_deg", d["roof_angle_deg"]); form.addRow("roof_gamma", d["roof_gamma"])
        form.addRow("alphak_file", d["alphak_file"]); form.addRow("zeta_local", d["zeta_local"]); form.addRow("friction_factor", d["friction_factor"])
        form.addRow("length_m", d["length_m"]); form.addRow("hydraulic_diameter_m", d["hydraulic_diameter_m"]); form.addRow("phi_min", d["phi_min"])
        for key, widget in d.items():
            if key == "box":
                continue
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._update_sketch)
                widget.valueChanged.connect(self._trigger_preview)
            elif hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self._update_sketch)
                widget.currentTextChanged.connect(self._trigger_preview)
            elif hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._update_sketch)
                widget.textChanged.connect(self._trigger_preview)
        return d

    def _single_group_from_widgets(self, d: dict) -> dict:
        roof = {"type": d["roof_type"].currentText()}
        if d["roof_len_m"].value() > 0:
            roof["len_m"] = float(d["roof_len_m"].value())
        if d["roof_angle_deg"].value() > 0:
            roof["angle_deg"] = float(d["roof_angle_deg"].value())
        if d["roof_gamma"].value() > 0:
            roof["gamma"] = float(d["roof_gamma"].value())
        return {
            "width_m": float(d["width_m"].value()),
            "height_m": float(d["height_m"].value()),
            "count": int(d["count"].value()),
            "offset_from_ut_m": float(d["offset_from_ut_m"].value()),
            "roof": roof,
            "alphak_file": d["alphak_file"].text().strip(),
            "channel": {
                "zeta_local": float(d["zeta_local"].value()),
                "friction_factor": float(d["friction_factor"].value()),
                "length_m": float(d["length_m"].value()),
                "hydraulic_diameter_m": float(d["hydraulic_diameter_m"].value()),
                "phi_min": float(d["phi_min"].value()),
            },
        }

    def _fill_single_group(self, d: dict, cfg: dict) -> None:
        roof = cfg.get("roof", {}) or {}
        channel = cfg.get("channel", {}) or {}
        d["width_m"].setValue(float(cfg.get("width_m", 0.01)))
        d["height_m"].setValue(float(cfg.get("height_m", 0.02)))
        d["count"].setValue(int(cfg.get("count", 1)))
        d["offset_from_ut_m"].setValue(float(cfg.get("offset_from_ut_m", 0.015)))
        d["roof_type"].setCurrentText(str(roof.get("type", "cos")))
        d["roof_len_m"].setValue(float(roof.get("len_m", 0.004)))
        d["roof_angle_deg"].setValue(float(roof.get("angle_deg", 20.0)))
        d["roof_gamma"].setValue(float(roof.get("gamma", 1.0)))
        d["alphak_file"].setText(str(cfg.get("alphak_file", "")))
        d["zeta_local"].setValue(float(channel.get("zeta_local", 1.0)))
        d["friction_factor"].setValue(float(channel.get("friction_factor", 0.02)))
        d["length_m"].setValue(float(channel.get("length_m", 0.03)))
        d["hydraulic_diameter_m"].setValue(float(channel.get("hydraulic_diameter_m", 0.01)))
        d["phi_min"].setValue(float(channel.get("phi_min", 0.2)))

    def _groups_from_table(self, table: QTableWidget) -> list[dict]:
        groups = []
        for r in range(table.rowCount()):
            roof = {"type": _item_text(table, r, 4, "none") or "none"}
            roof_len = _item_text(table, r, 5, "")
            roof_angle = _item_text(table, r, 6, "")
            roof_gamma = _item_text(table, r, 7, "")
            if roof_len:
                roof["len_m"] = float(roof_len)
            if roof_angle:
                roof["angle_deg"] = float(roof_angle)
            if roof_gamma:
                roof["gamma"] = float(roof_gamma)
            groups.append({
                "width_m": _item_float(table, r, 0, 0.01),
                "height_m": _item_float(table, r, 1, 0.02),
                "count": _item_int(table, r, 2, 1),
                "offset_from_ut_m": _item_float(table, r, 3, 0.0),
                "roof": roof,
                "alphak_file": _item_text(table, r, 8, ""),
                "channel": {
                    "zeta_local": _item_float(table, r, 9, 1.0),
                    "friction_factor": _item_float(table, r, 10, 0.02),
                    "length_m": _item_float(table, r, 11, 0.03),
                    "hydraulic_diameter_m": _item_float(table, r, 12, 0.01),
                    "phi_min": _item_float(table, r, 13, 0.2),
                },
            })
        return groups

    def _load_table(self, table: QTableWidget, groups: list[dict]) -> None:
        table.blockSignals(True)
        table.setRowCount(0)
        for g in groups:
            self._append_row(table, g)
        table.blockSignals(False)

    def _update_sketch(self, *args) -> None:
        self.sketch.set_slot_config({
            "intake": self._single_group_from_widgets(self.single_intake),
            "exhaust": self._single_group_from_widgets(self.single_exhaust),
            "intake_groups": self._groups_from_table(self.intake_table),
            "exhaust_groups": self._groups_from_table(self.exhaust_table),
        })

    def set_config(self, cfg: dict) -> None:
        s = cfg["gasexchange"]["slots"]
        self.default_ak_file.setText(str(s.get("alphak_file", "")))
        self._fill_single_group(self.single_intake, s.get("intake", {}))
        self._fill_single_group(self.single_exhaust, s.get("exhaust", {}))
        self._load_table(self.intake_table, s.get("intake_groups", []))
        self._load_table(self.exhaust_table, s.get("exhaust_groups", []))
        self._update_sketch()
        self._trigger_preview()

    def update_config(self, cfg: dict) -> None:
        cfg["gasexchange"]["slots"] = {
            "alphak_file": self.default_ak_file.text().strip(),
            "intake": self._single_group_from_widgets(self.single_intake),
            "exhaust": self._single_group_from_widgets(self.single_exhaust),
            "intake_groups": self._groups_from_table(self.intake_table),
            "exhaust_groups": self._groups_from_table(self.exhaust_table),
        }


class GasExchangeTab(BasicTab):
    def __init__(self):
        super().__init__("Gas exchange")
        top = QGroupBox("General")
        f = QFormLayout(top)
        self.enabled = ConfigFieldFactory.check(True)
        self.mode = ConfigFieldFactory.combo(["valves", "ports", "slots"], "slots")
        self.flow_model = ConfigFieldFactory.combo(["nozzle_choked", "simple_orifice"], "nozzle_choked")
        self.preview_source = ConfigFieldFactory.combo(["auto", "valves", "ports", "slots"], "auto")
        f.addRow("Enabled", self.enabled)
        f.addRow("Mode", self.mode)
        f.addRow("Flow model", self.flow_model)
        f.addRow("Timing preview", self.preview_source)
        self.layout.addWidget(top)

        self.mode_hint = QLabel("")
        self.mode_hint.setWordWrap(True)
        self.mode_hint.setStyleSheet("padding: 6px 10px; border: 1px solid #dbe4f0; border-radius: 10px;")
        self.layout.addWidget(self.mode_hint)

        self.stack = QStackedWidget()

        self.valves_page = QWidget()
        vl = QVBoxLayout(self.valves_page)
        vl.setContentsMargins(0, 0, 0, 0)
        self.valves = ValvesTab()
        vl.addWidget(self.valves)

        self.ports_page = QWidget()
        pl = QVBoxLayout(self.ports_page)
        pl.setContentsMargins(0, 0, 0, 0)
        self.ports = PortsTab()
        pl.addWidget(self.ports)

        self.slots_page = QWidget()
        sl = QVBoxLayout(self.slots_page)
        sl.setContentsMargins(0, 0, 0, 0)
        self.slots = SlotsTab()
        sl.addWidget(self.slots)

        self.stack.addWidget(self.valves_page)
        self.stack.addWidget(self.ports_page)
        self.stack.addWidget(self.slots_page)
        self.layout.addWidget(self.stack)

        self.context_info = QGroupBox("Context-sensitive fields")
        ci = QVBoxLayout(self.context_info)
        self.context_label = QLabel("")
        self.context_label.setWordWrap(True)
        ci.addWidget(self.context_label)
        self.layout.addWidget(self.context_info)

        self.mode.currentTextChanged.connect(self._sync_mode_ui)
        self.preview_source.currentTextChanged.connect(self._sync_preview_hint)

        self._sync_mode_ui(self.mode.currentText())
        self._sync_preview_hint()

    def _sync_preview_hint(self) -> None:
        src = self.preview_source.currentText()
        mode = self.mode.currentText()
        selected = mode if src == "auto" else src
        hint = {
            "valves": "Preview target: valve preview widget",
            "ports": "Preview target: timing diagram dock (ports)",
            "slots": "Preview target: slot preview widget",
        }.get(selected, "Preview target: automatic")
        mode_text = {
            "valves": "Active mode: valves.",
            "ports": "Active mode: ports.",
            "slots": "Active mode: slots.",
        }.get(mode, "Active mode changed.")
        self.mode_hint.setText(f"{mode_text} {hint}")

    def _sync_mode_ui(self, mode: str) -> None:
        mode = str(mode)
        mapping = {"valves": 0, "ports": 1, "slots": 2}
        self.stack.setCurrentIndex(mapping.get(mode, 0))

        if mode == "valves":
            self.context_label.setText(
                "Visible now: valve lift files, alphaK (bezogen auf Kolbenfläche), diameters, timing shift and scaling. "
                "Ports and slots are hidden because they are not relevant for the active gas exchange mode."
            )
        elif mode == "ports":
            self.context_label.setText(
                "Visible now: port area file and port alphaK file. "
                "Valve lift/scaling fields and slot geometry are hidden because they are not relevant for ports."
            )
        else:
            self.context_label.setText(
                "Visible now: slot geometry, roof, groups and slot alphaK/channel settings. "
                "Valve and port specific fields are hidden because they are not relevant for slots."
            )

        self._sync_preview_hint()

    def set_config(self, cfg: dict) -> None:
        gx = cfg["gasexchange"]
        self.enabled.setChecked(bool(gx.get("enabled", True)))
        self.mode.setCurrentText(str(gx.get("mode", "slots")))
        self.flow_model.setCurrentText(str(gx.get("flow_model", "nozzle_choked")))
        src = str(gx.get("preview_source", "auto"))
        self.preview_source.setCurrentText(src if self.preview_source.findText(src) >= 0 else "auto")
        self.valves.set_config(cfg)
        self.ports.set_config(cfg)
        self.slots.set_config(cfg)
        self._sync_mode_ui(self.mode.currentText())

    def update_config(self, cfg: dict) -> None:
        cfg["gasexchange"]["enabled"] = bool(self.enabled.isChecked())
        cfg["gasexchange"]["mode"] = self.mode.currentText()
        cfg["gasexchange"]["flow_model"] = self.flow_model.currentText()
        cfg["gasexchange"]["preview_source"] = self.preview_source.currentText()
        self.valves.update_config(cfg)
        self.ports.update_config(cfg)
        self.slots.update_config(cfg)


class UserCylinderAssemblyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = {}
        self._user_cyl = {}
        self._gx = {}
        self.node_rect_map = {}
        self.node_click_callback = None
        self.setMinimumHeight(360)

    def set_data(self, engine_cfg: dict, user_cylinder_cfg: dict, gx_cfg: dict) -> None:
        self._engine = dict(engine_cfg or {})
        self._user_cyl = dict(user_cylinder_cfg or {})
        self._gx = dict(gx_cfg or {})
        self.update()

    
    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        for name, rect in self.node_rect_map.items():
            if rect.contains(pos):
                if self.node_click_callback:
                    self.node_click_callback(name)
                break


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(10, 10, -10, -10)

        is_light = self.palette().window().color().lightness() > 128
        bg = QColor("#ffffff") if is_light else QColor("#111827")
        fg = QColor("#1f2937") if is_light else QColor("#e5e7eb")
        muted = QColor("#64748b") if is_light else QColor("#94a3b8")
        grid = QColor("#dbe3ef") if is_light else QColor("#243041")
        cyl_fill = QColor("#f8fbff") if is_light else QColor("#0f172a")
        intake_col = QColor("#3b82f6")
        exhaust_col = QColor("#ef4444")
        port_fill = QColor(59, 130, 246, 80) if is_light else QColor(59, 130, 246, 120)
        slot_fill = QColor(239, 68, 68, 80) if is_light else QColor(239, 68, 68, 120)

        p.fillRect(r, bg)
        p.setPen(QPen(grid, 1))
        p.drawRoundedRect(r, 14, 14)

        bore = float(self._engine.get("bore_m", 0.086))
        stroke = float(self._engine.get("stroke_m", 0.086))
        conrod = float(self._engine.get("conrod_m", 0.143))
        cr = float(self._engine.get("compression_ratio", 10.5))

        uc = self._user_cyl
        gx = self._gx
        act = str(uc.get("actuation_source", "auto"))
        gx_mode = str(gx.get("mode", "valves"))
        effective_act = gx_mode if act == "auto" else act

        # main geometry block
        cyl = QRectF(r.left() + 150, r.top() + 40, max(260.0, r.width() * 0.42), r.height() - 95)
        p.setPen(QPen(fg, 2))
        p.setBrush(QBrush(cyl_fill))
        p.drawRoundedRect(cyl, 18, 18)

        # head
        head_h = max(24.0, cyl.height() * 0.10)
        head_rect = QRectF(cyl.left() + 16, cyl.top() + 8, cyl.width() - 32, head_h)
        p.setBrush(QBrush(QColor("#cbd5e1") if is_light else QColor("#334155")))
        p.drawRoundedRect(head_rect, 10, 10)

        # piston
        piston_h = max(28.0, cyl.height() * 0.11)
        piston_y = cyl.bottom() - piston_h - cyl.height() * 0.22
        piston_rect = QRectF(cyl.left() + 24, piston_y, cyl.width() - 48, piston_h)
        p.setBrush(QBrush(QColor("#94a3b8") if is_light else QColor("#475569")))
        p.drawRoundedRect(piston_rect, 10, 10)

        # liner wall markers
        p.setPen(QPen(QColor("#0ea5e9") if is_light else QColor("#38bdf8"), 3))
        p.drawLine(int(cyl.left() + 8), int(head_rect.bottom() + 8), int(cyl.left() + 8), int(cyl.bottom() - 8))
        p.drawLine(int(cyl.right() - 8), int(head_rect.bottom() + 8), int(cyl.right() - 8), int(cyl.bottom() - 8))

        # connecting rod
        rod_x = cyl.center().x()
        p.setPen(QPen(QColor("#64748b") if is_light else QColor("#94a3b8"), 5))
        p.drawLine(int(rod_x), int(piston_rect.bottom()), int(rod_x), int(cyl.bottom() + 34))
        p.setPen(QPen(fg, 1))
        p.drawEllipse(int(rod_x - 8), int(cyl.bottom() + 28), 16, 16)

        # annotate main parts
        p.setPen(QPen(fg, 1))
        p.drawText(int(cyl.left()), int(head_rect.top() - 8), "Head")
        p.drawText(int(cyl.left()), int((head_rect.bottom() + piston_rect.top()) / 2), "Liner")
        p.drawText(int(cyl.left()), int(piston_rect.center().y() + 5), "Piston")

        # actuation visual
        if effective_act == "valves":
            # intake valve left top
            ivx = cyl.left() + cyl.width() * 0.30
            evx = cyl.left() + cyl.width() * 0.70
            stem_top = head_rect.top() - 28
            seat_y = head_rect.bottom() + 4

            p.setPen(QPen(intake_col, 3))
            p.drawLine(int(ivx), int(stem_top), int(ivx), int(seat_y))
            p.drawLine(int(ivx - 14), int(seat_y + 8), int(ivx), int(seat_y))
            p.drawLine(int(ivx + 14), int(seat_y + 8), int(ivx), int(seat_y))
            p.drawText(int(ivx - 34), int(stem_top - 8), "Intake valve")

            p.setPen(QPen(exhaust_col, 3))
            p.drawLine(int(evx), int(stem_top), int(evx), int(seat_y))
            p.drawLine(int(evx - 14), int(seat_y + 8), int(evx), int(seat_y))
            p.drawLine(int(evx + 14), int(seat_y + 8), int(evx), int(seat_y))
            p.drawText(int(evx - 38), int(stem_top - 8), "Exhaust valve")

        elif effective_act in ("ports", "slots"):
            # port/slot windows near lower liner
            p.setPen(QPen(intake_col, 1))
            for i in range(4):
                yy = piston_rect.bottom() - 18 - i * 18
                rect = QRectF(cyl.left() - 10, yy, 14, 12)
                p.fillRect(rect, port_fill)
                p.drawRect(rect)
            p.drawText(int(cyl.left() - 82), int(piston_rect.bottom() - 95), "Intake ports" if effective_act == "ports" else "Intake slots")

            p.setPen(QPen(exhaust_col, 1))
            for i in range(4):
                yy = piston_rect.bottom() - 18 - i * 18
                rect = QRectF(cyl.right() - 4, yy, 14, 12)
                p.fillRect(rect, slot_fill)
                p.drawRect(rect)
            p.drawText(int(cyl.right() + 16), int(piston_rect.bottom() - 95), "Exhaust ports" if effective_act == "ports" else "Exhaust slots")

        # manifold connection blocks
        box_w = 150
        left_box = QRectF(r.left() + 18, r.top() + 86, box_w, 54)
        right_box = QRectF(r.right() - box_w - 18, r.top() + 86, box_w, 54)

        p.setPen(QPen(intake_col, 2))
        p.setBrush(QBrush(QColor(219, 234, 254, 140) if is_light else QColor(30, 64, 175, 90)))
        p.drawRoundedRect(left_box, 12, 12)
        p.drawText(left_box.adjusted(8, 8, -8, -8), Qt.AlignLeft | Qt.AlignTop, f"Intake\n{uc.get('connections', {}).get('intake_name', 'intake_manifold_1')}")

        p.setPen(QPen(exhaust_col, 2))
        p.setBrush(QBrush(QColor(254, 226, 226, 140) if is_light else QColor(127, 29, 29, 90)))
        p.drawRoundedRect(right_box, 12, 12)
        p.drawText(right_box.adjusted(8, 8, -8, -8), Qt.AlignLeft | Qt.AlignTop, f"Exhaust\n{uc.get('connections', {}).get('exhaust_name', 'exhaust_manifold_1')}")

        # connection lines
        p.setPen(QPen(intake_col, 2, Qt.DashLine))
        p.drawLine(int(left_box.right()), int(left_box.center().y()), int(cyl.left()), int(left_box.center().y()))
        p.setPen(QPen(exhaust_col, 2, Qt.DashLine))
        p.drawLine(int(cyl.right()), int(right_box.center().y()), int(right_box.left()), int(right_box.center().y()))

        # info cards
        info_x = cyl.right() + 40
        info_y = cyl.top() + 188
        uc_name = str(uc.get("name", "user_cylinder_1"))
        notes = str(uc.get("notes", ""))
        p.setPen(QPen(fg, 1))
        p.drawText(int(info_x), int(cyl.top() + 18), f"User Cylinder: {uc_name}")
        p.drawText(int(info_x), int(cyl.top() + 42), f"Actuation: {effective_act} ({act})")
        p.drawText(int(info_x), int(cyl.top() + 66), f"Offset: {float(uc.get('crank_angle_offset_deg', 0.0)):.1f} deg KW")
        p.drawText(int(info_x), int(cyl.top() + 90), f"Bore: {bore:.4f} m")
        p.drawText(int(info_x), int(cyl.top() + 114), f"Stroke: {stroke:.4f} m")
        p.drawText(int(info_x), int(cyl.top() + 138), f"Conrod: {conrod:.4f} m")
        p.drawText(int(info_x), int(cyl.top() + 162), f"CR: {cr:.2f}")

        piston = uc.get("piston", {})
        liner = uc.get("liner", {})
        head = uc.get("head", {})
        p.drawText(int(info_x), int(info_y), f"Piston area_scale: {float(piston.get('area_scale', 1.0)):.3f}")
        p.drawText(int(info_x), int(info_y + 24), f"Piston T: {float(piston.get('crown_temperature_K', 520.0)):.1f} K")
        p.drawText(int(info_x), int(info_y + 54), f"Liner area_scale: {float(liner.get('area_scale', 1.0)):.3f}")
        p.drawText(int(info_x), int(info_y + 78), f"Liner T: {float(liner.get('wall_temperature_K', 430.0)):.1f} K")
        p.drawText(int(info_x), int(info_y + 108), f"Head area_scale: {float(head.get('area_scale', 1.0)):.3f}")
        p.drawText(int(info_x), int(info_y + 132), f"Head T: {float(head.get('wall_temperature_K', 480.0)):.1f} K")

        runners = uc.get("runners", {})
        rin = runners.get("intake", {})
        rex = runners.get("exhaust", {})
        p.setPen(QPen(fg, 1))
        p.drawText(int(info_x), int(info_y + 160), f"Runner in: L={float(rin.get('length_m', 0.0)):.3f} m, D={float(rin.get('diameter_m', 0.0)):.3f} m")
        p.drawText(int(info_x), int(info_y + 184), f"Runner ex: L={float(rex.get('length_m', 0.0)):.3f} m, D={float(rex.get('diameter_m', 0.0)):.3f} m")
        if notes:
            p.setPen(QPen(muted, 1))
            p.drawText(QRectF(info_x, info_y + 170, max(220.0, r.right() - info_x - 10), 90), Qt.TextWordWrap, f"Notes:\n{notes}")



class UserCylinderTab(BasicTab):
    def __init__(self):
        super().__init__("User cylinder")
        self._assembly_callback = None
        self._items: list[dict] = []
        self._loading = False

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Cylinder list"))
        self.active_name = QComboBox()
        self.btn_add = QPushButton("Add cylinder")
        self.btn_remove = QPushButton("Remove cylinder")
        self.btn_duplicate = QPushButton("Duplicate cylinder")
        toolbar.addWidget(self.active_name, 1)
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_duplicate)
        toolbar.addWidget(self.btn_remove)
        self.layout.addLayout(toolbar)

        body = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        self.cylinder_list = QListWidget()
        ll.addWidget(self.cylinder_list)

        right = QWidget()
        rl = QVBoxLayout(right)

        grid = QGridLayout()

        box1 = QGroupBox("General")
        f1 = QFormLayout(box1)
        self.name = ConfigFieldFactory.line("user_cylinder_1")
        self.enabled = ConfigFieldFactory.check(True)
        self.crank_angle_offset_deg = ConfigFieldFactory.dspin(0.0, -7200.0, 7200.0, 1.0, 3)
        self.actuation_source = ConfigFieldFactory.combo(["auto", "valves", "ports", "slots"], "auto")
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(100)
        f1.addRow("name", self.name)
        f1.addRow("enabled", self.enabled)
        f1.addRow("crank_angle_offset_deg", self.crank_angle_offset_deg)
        f1.addRow("actuation_source", self.actuation_source)
        f1.addRow("notes", self.notes)

        box2 = QGroupBox("Connections")
        f2 = QFormLayout(box2)
        self.intake_name = ConfigFieldFactory.line("intake_manifold_1")
        self.exhaust_name = ConfigFieldFactory.line("exhaust_manifold_1")
        f2.addRow("intake_name", self.intake_name)
        f2.addRow("exhaust_name", self.exhaust_name)

        box3 = QGroupBox("Piston")
        f3 = QFormLayout(box3)
        self.piston_area_scale = ConfigFieldFactory.dspin(1.0, 0.01, 100.0, 0.01, 4)
        self.piston_temp = ConfigFieldFactory.dspin(520.0, 0.0, 5000.0, 1.0, 2)
        f3.addRow("area_scale", self.piston_area_scale)
        f3.addRow("crown_temperature_K", self.piston_temp)

        box4 = QGroupBox("Liner")
        f4 = QFormLayout(box4)
        self.liner_area_scale = ConfigFieldFactory.dspin(1.0, 0.01, 100.0, 0.01, 4)
        self.liner_temp = ConfigFieldFactory.dspin(430.0, 0.0, 5000.0, 1.0, 2)
        f4.addRow("area_scale", self.liner_area_scale)
        f4.addRow("wall_temperature_K", self.liner_temp)

        box5 = QGroupBox("Head")
        f5 = QFormLayout(box5)
        self.head_area_scale = ConfigFieldFactory.dspin(1.0, 0.01, 100.0, 0.01, 4)
        self.head_temp = ConfigFieldFactory.dspin(480.0, 0.0, 5000.0, 1.0, 2)
        f5.addRow("area_scale", self.head_area_scale)
        f5.addRow("wall_temperature_K", self.head_temp)


        box6 = QGroupBox("Intake runner")
        f6 = QFormLayout(box6)
        self.rin_enabled = ConfigFieldFactory.check(True)
        self.rin_length = ConfigFieldFactory.dspin(0.25, 0.0, 100.0, 0.01, 4)
        self.rin_diameter = ConfigFieldFactory.dspin(0.035, 0.0, 10.0, 0.001, 5)
        self.rin_volume = ConfigFieldFactory.dspin(0.00024, 0.0, 10.0, 0.00001, 8)
        self.rin_zeta = ConfigFieldFactory.dspin(1.2, 0.0, 1000.0, 0.1, 4)
        self.rin_fric = ConfigFieldFactory.dspin(0.03, 0.0, 10.0, 0.01, 4)
        self.rin_temp = ConfigFieldFactory.dspin(320.0, 0.0, 5000.0, 1.0, 2)
        f6.addRow("enabled", self.rin_enabled)
        f6.addRow("length_m", self.rin_length)
        f6.addRow("diameter_m", self.rin_diameter)
        f6.addRow("volume_m3", self.rin_volume)
        f6.addRow("zeta_local", self.rin_zeta)
        f6.addRow("friction_factor", self.rin_fric)
        f6.addRow("wall_temperature_K", self.rin_temp)

        box7 = QGroupBox("Exhaust runner")
        f7 = QFormLayout(box7)
        self.rex_enabled = ConfigFieldFactory.check(True)
        self.rex_length = ConfigFieldFactory.dspin(0.35, 0.0, 100.0, 0.01, 4)
        self.rex_diameter = ConfigFieldFactory.dspin(0.030, 0.0, 10.0, 0.001, 5)
        self.rex_volume = ConfigFieldFactory.dspin(0.00025, 0.0, 10.0, 0.00001, 8)
        self.rex_zeta = ConfigFieldFactory.dspin(1.8, 0.0, 1000.0, 0.1, 4)
        self.rex_fric = ConfigFieldFactory.dspin(0.04, 0.0, 10.0, 0.01, 4)
        self.rex_temp = ConfigFieldFactory.dspin(650.0, 0.0, 5000.0, 1.0, 2)
        f7.addRow("enabled", self.rex_enabled)
        f7.addRow("length_m", self.rex_length)
        f7.addRow("diameter_m", self.rex_diameter)
        f7.addRow("volume_m3", self.rex_volume)
        f7.addRow("zeta_local", self.rex_zeta)
        f7.addRow("friction_factor", self.rex_fric)
        f7.addRow("wall_temperature_K", self.rex_temp)

        self.assembly = UserCylinderAssemblyWidget()

        info = QGroupBox("Info")
        fi = QVBoxLayout(info)
        fi.addWidget(QLabel(
            "Mehrere User Cylinder können jetzt verwaltet werden.\n"
            "Die Simulation verwendet jetzt einen gemeinsamen globalen Winkel und separate Zustände je aktiviertem Cylinder.\n\n"
            "Je Cylinder konfigurierbar:\n"
            "- actuation source\n"
            "- intake/exhaust connections\n"
            "- piston / liner / head zones\n"
            "- intake/exhaust runner model"
        ))

        grid.addWidget(box1, 0, 0)
        grid.addWidget(box2, 0, 1)
        grid.addWidget(box3, 1, 0)
        grid.addWidget(box4, 1, 1)
        grid.addWidget(box5, 2, 0)
        grid.addWidget(info, 2, 1)
        grid.addWidget(box6, 3, 0)
        grid.addWidget(box7, 3, 1)

        rl.addLayout(grid)
        rl.addWidget(self.assembly, 1)

        body.addWidget(left)
        body.addWidget(right)
        body.setSizes([240, 1100])
        self.layout.addWidget(body, 1)

        self.btn_add.clicked.connect(self._add_cylinder)
        self.btn_remove.clicked.connect(self._remove_current_cylinder)
        self.btn_duplicate.clicked.connect(self._duplicate_current_cylinder)
        self.cylinder_list.currentRowChanged.connect(self._load_current_row)
        self.active_name.currentTextChanged.connect(self._emit_update)

        _widgets = [
            self.name, self.enabled, self.crank_angle_offset_deg, self.actuation_source, self.intake_name, self.exhaust_name,
            self.piston_area_scale, self.piston_temp, self.liner_area_scale, self.liner_temp,
            self.head_area_scale, self.head_temp,
            self.rin_enabled, self.rin_length, self.rin_diameter, self.rin_volume, self.rin_zeta, self.rin_fric, self.rin_temp,
            self.rex_enabled, self.rex_length, self.rex_diameter, self.rex_volume, self.rex_zeta, self.rex_fric, self.rex_temp,
        ]
        for _w in _widgets:
            if hasattr(_w, "valueChanged"):
                _w.valueChanged.connect(self._store_current_row)
            elif hasattr(_w, "currentTextChanged"):
                _w.currentTextChanged.connect(self._store_current_row)
            elif hasattr(_w, "stateChanged"):
                _w.stateChanged.connect(self._store_current_row)
            elif hasattr(_w, "textChanged"):
                _w.textChanged.connect(self._store_current_row)
        self.notes.textChanged.connect(self._store_current_row)

    def set_assembly_callback(self, callback) -> None:
        self._assembly_callback = callback

    def _emit_update(self, *args) -> None:
        if self._assembly_callback is not None:
            self._assembly_callback()

    def _default_item(self, name: str) -> dict:
        return {
            "name": name,
            "enabled": True,
            "crank_angle_offset_deg": 0.0,
            "actuation_source": "auto",
            "notes": "",
            "connections": {"intake_name": f"{name}_intake", "exhaust_name": f"{name}_exhaust"},
            "runners": {
                "intake": {"enabled": True, "length_m": 0.25, "diameter_m": 0.035, "volume_m3": 0.00024, "zeta_local": 1.2, "friction_factor": 0.03, "wall_temperature_K": 320.0},
                "exhaust": {"enabled": True, "length_m": 0.35, "diameter_m": 0.030, "volume_m3": 0.00025, "zeta_local": 1.8, "friction_factor": 0.04, "wall_temperature_K": 650.0},
            },
            "piston": {"area_scale": 1.0, "crown_temperature_K": 520.0},
            "liner": {"area_scale": 1.0, "wall_temperature_K": 430.0},
            "head": {"area_scale": 1.0, "wall_temperature_K": 480.0},
        }

    def _refresh_list_widgets(self, active_name: str | None = None) -> None:
        self._loading = True
        self.cylinder_list.clear()
        self.active_name.clear()
        for item in self._items:
            label = f"{item.get('name', 'cylinder')} [{float(item.get('crank_angle_offset_deg', 0.0)):.0f}°] {'(on)' if item.get('enabled', True) else '(off)'}"
            self.cylinder_list.addItem(label)
            self.active_name.addItem(item.get("name", "cylinder"))
        if self._items:
            idx = 0
            if active_name:
                for i, item in enumerate(self._items):
                    if item.get("name") == active_name:
                        idx = i
                        break
            self.cylinder_list.setCurrentRow(idx)
            self.active_name.setCurrentText(self._items[idx].get("name", "cylinder"))
        self._loading = False

    def _current_item_from_form(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "enabled": bool(self.enabled.isChecked()),
            "crank_angle_offset_deg": float(self.crank_angle_offset_deg.value()),
            "actuation_source": self.actuation_source.currentText(),
            "notes": self.notes.toPlainText().strip(),
            "connections": {
                "intake_name": self.intake_name.text().strip(),
                "exhaust_name": self.exhaust_name.text().strip(),
            },
            "runners": {
                "intake": {
                    "enabled": bool(self.rin_enabled.isChecked()),
                    "length_m": float(self.rin_length.value()),
                    "diameter_m": float(self.rin_diameter.value()),
                    "volume_m3": float(self.rin_volume.value()),
                    "zeta_local": float(self.rin_zeta.value()),
                    "friction_factor": float(self.rin_fric.value()),
                    "wall_temperature_K": float(self.rin_temp.value()),
                },
                "exhaust": {
                    "enabled": bool(self.rex_enabled.isChecked()),
                    "length_m": float(self.rex_length.value()),
                    "diameter_m": float(self.rex_diameter.value()),
                    "volume_m3": float(self.rex_volume.value()),
                    "zeta_local": float(self.rex_zeta.value()),
                    "friction_factor": float(self.rex_fric.value()),
                    "wall_temperature_K": float(self.rex_temp.value()),
                },
            },
            "piston": {
                "area_scale": float(self.piston_area_scale.value()),
                "crown_temperature_K": float(self.piston_temp.value()),
            },
            "liner": {
                "area_scale": float(self.liner_area_scale.value()),
                "wall_temperature_K": float(self.liner_temp.value()),
            },
            "head": {
                "area_scale": float(self.head_area_scale.value()),
                "wall_temperature_K": float(self.head_temp.value()),
            },
        }

    def _apply_item_to_form(self, uc: dict, engine_cfg: dict | None = None, gx_cfg: dict | None = None) -> None:
        self._loading = True
        self.name.setText(str(uc.get("name", "user_cylinder_1")))
        self.enabled.setChecked(bool(uc.get("enabled", True)))
        self.crank_angle_offset_deg.setValue(float(uc.get("crank_angle_offset_deg", 0.0)))
        self.actuation_source.setCurrentText(str(uc.get("actuation_source", "auto")))
        self.notes.setPlainText(str(uc.get("notes", "")))
        con = uc.get("connections", {})
        self.intake_name.setText(str(con.get("intake_name", "intake_manifold_1")))
        self.exhaust_name.setText(str(con.get("exhaust_name", "exhaust_manifold_1")))
        r = uc.get("runners", {})
        ri = r.get("intake", {})
        re = r.get("exhaust", {})
        self.rin_enabled.setChecked(bool(ri.get("enabled", True)))
        self.rin_length.setValue(float(ri.get("length_m", 0.25)))
        self.rin_diameter.setValue(float(ri.get("diameter_m", 0.035)))
        self.rin_volume.setValue(float(ri.get("volume_m3", 0.00024)))
        self.rin_zeta.setValue(float(ri.get("zeta_local", 1.2)))
        self.rin_fric.setValue(float(ri.get("friction_factor", 0.03)))
        self.rin_temp.setValue(float(ri.get("wall_temperature_K", 320.0)))
        self.rex_enabled.setChecked(bool(re.get("enabled", True)))
        self.rex_length.setValue(float(re.get("length_m", 0.35)))
        self.rex_diameter.setValue(float(re.get("diameter_m", 0.030)))
        self.rex_volume.setValue(float(re.get("volume_m3", 0.00025)))
        self.rex_zeta.setValue(float(re.get("zeta_local", 1.8)))
        self.rex_fric.setValue(float(re.get("friction_factor", 0.04)))
        self.rex_temp.setValue(float(re.get("wall_temperature_K", 650.0)))
        p = uc.get("piston", {})
        self.piston_area_scale.setValue(float(p.get("area_scale", 1.0)))
        self.piston_temp.setValue(float(p.get("crown_temperature_K", 520.0)))
        l = uc.get("liner", {})
        self.liner_area_scale.setValue(float(l.get("area_scale", 1.0)))
        self.liner_temp.setValue(float(l.get("wall_temperature_K", 430.0)))
        h = uc.get("head", {})
        self.head_area_scale.setValue(float(h.get("area_scale", 1.0)))
        self.head_temp.setValue(float(h.get("wall_temperature_K", 480.0)))
        self._loading = False
        self.assembly.set_data(engine_cfg or {}, uc, gx_cfg or {})

    def _store_current_row(self, *args) -> None:
        if self._loading:
            return
        row = self.cylinder_list.currentRow()
        if row < 0 or row >= len(self._items):
            return
        self._items[row] = self._current_item_from_form()
        cur_name = self._items[row].get("name", "cylinder")
        self._refresh_list_widgets(active_name=self.active_name.currentText() if self.active_name.currentText() else cur_name)
        self.cylinder_list.setCurrentRow(row)
        self.active_name.setCurrentText(cur_name if self.active_name.findText(cur_name) >= 0 else self.active_name.currentText())
        self._emit_update()

    def _load_current_row(self, row: int) -> None:
        if self._loading:
            return
        if row < 0 or row >= len(self._items):
            return
        self._apply_item_to_form(self._items[row])
        self._emit_update()

    def _add_cylinder(self) -> None:
        base = "user_cylinder"
        idx = len(self._items) + 1
        names = {it.get("name") for it in self._items}
        while f"{base}_{idx}" in names:
            idx += 1
        item = self._default_item(f"{base}_{idx}")
        self._items.append(item)
        self._refresh_list_widgets(active_name=item["name"])
        self._emit_update()

    def _duplicate_current_cylinder(self) -> None:
        row = self.cylinder_list.currentRow()
        if row < 0 or row >= len(self._items):
            return
        src = json.loads(json.dumps(self._items[row]))
        base = src.get("name", "user_cylinder")
        new_name = f"{base}_copy"
        names = {it.get("name") for it in self._items}
        idx = 2
        candidate = new_name
        while candidate in names:
            candidate = f"{new_name}_{idx}"
            idx += 1
        src["name"] = candidate
        self._items.append(src)
        self._refresh_list_widgets(active_name=candidate)
        self._emit_update()

    def _remove_current_cylinder(self) -> None:
        if len(self._items) <= 1:
            return
        row = self.cylinder_list.currentRow()
        if row < 0 or row >= len(self._items):
            return
        del self._items[row]
        new_row = min(row, len(self._items) - 1)
        active_name = self._items[new_row].get("name", "user_cylinder_1")
        self._refresh_list_widgets(active_name=active_name)
        self._emit_update()

    def set_config(self, cfg: dict) -> None:
        self._items = json.loads(json.dumps(cfg.get("user_cylinders", [])))
        if not self._items:
            self._items = [self._default_item("user_cylinder_1")]
        self._refresh_list_widgets(active_name=cfg.get("active_user_cylinder", self._items[0].get("name", "user_cylinder_1")))
        row = self.cylinder_list.currentRow()
        if row < 0:
            row = 0
            self.cylinder_list.setCurrentRow(0)
        self._apply_item_to_form(self._items[row], cfg.get("engine", {}), cfg.get("gasexchange", {}))

    def update_config(self, cfg: dict) -> None:
        row = self.cylinder_list.currentRow()
        if 0 <= row < len(self._items):
            self._items[row] = self._current_item_from_form()
        cfg["user_cylinders"] = json.loads(json.dumps(self._items))
        cfg["active_user_cylinder"] = self.active_name.currentText() if self.active_name.currentText() else self._items[0].get("name", "user_cylinder_1")



class PlenaTab(BasicTab):
    def __init__(self):
        super().__init__("Dynamic intake / exhaust plena")
        grid = QGridLayout()

        box0 = QGroupBox("General")
        f0 = QFormLayout(box0)
        self.enabled = ConfigFieldFactory.check(True)
        f0.addRow("enabled", self.enabled)

        box1 = QGroupBox("Intake plenum")
        f1 = QFormLayout(box1)
        self.int_volume = ConfigFieldFactory.dspin(0.012, 1e-6, 10.0, 0.001, 6)
        self.int_p0 = ConfigFieldFactory.dspin(100000.0, 0.0, 1e9, 1000.0, 3)
        self.int_T0 = ConfigFieldFactory.dspin(300.0, 0.0, 5000.0, 1.0, 3)
        f1.addRow("volume_m3", self.int_volume)
        f1.addRow("p0_pa", self.int_p0)
        f1.addRow("T0_K", self.int_T0)

        box2 = QGroupBox("Exhaust plenum")
        f2 = QFormLayout(box2)
        self.ex_volume = ConfigFieldFactory.dspin(0.018, 1e-6, 10.0, 0.001, 6)
        self.ex_p0 = ConfigFieldFactory.dspin(105000.0, 0.0, 1e9, 1000.0, 3)
        self.ex_T0 = ConfigFieldFactory.dspin(650.0, 0.0, 5000.0, 1.0, 3)
        f2.addRow("volume_m3", self.ex_volume)
        f2.addRow("p0_pa", self.ex_p0)
        f2.addRow("T0_K", self.ex_T0)

        info = QGroupBox("Info")
        vi = QVBoxLayout(info)
        vi.addWidget(QLabel(
            "Diese Version verwendet dynamische Zustände für:\n"
            "- intake plenum mass / temperature / pressure\n"
            "- exhaust plenum mass / temperature / pressure\n\n"
            "Die Cylinder sind damit über gemeinsame Volumina gekoppelt."
        ))

        grid.addWidget(box0, 0, 0)
        grid.addWidget(box1, 1, 0)
        grid.addWidget(box2, 1, 1)
        grid.addWidget(info, 0, 1)
        self.layout.addLayout(grid)

    def set_config(self, cfg: dict) -> None:
        pl = cfg.get("plena", {})
        self.enabled.setChecked(bool(pl.get("enabled", True)))
        i = pl.get("intake", {})
        e = pl.get("exhaust", {})
        self.int_volume.setValue(float(i.get("volume_m3", 0.012)))
        self.int_p0.setValue(float(i.get("p0_pa", 100000.0)))
        self.int_T0.setValue(float(i.get("T0_K", 300.0)))
        self.ex_volume.setValue(float(e.get("volume_m3", 0.018)))
        self.ex_p0.setValue(float(e.get("p0_pa", 105000.0)))
        self.ex_T0.setValue(float(e.get("T0_K", 650.0)))

    def update_config(self, cfg: dict) -> None:
        cfg["plena"] = {
            "enabled": bool(self.enabled.isChecked()),
            "intake": {
                "volume_m3": float(self.int_volume.value()),
                "p0_pa": float(self.int_p0.value()),
                "T0_K": float(self.int_T0.value()),
            },
            "exhaust": {
                "volume_m3": float(self.ex_volume.value()),
                "p0_pa": float(self.ex_p0.value()),
                "T0_K": float(self.ex_T0.value()),
            },
        }



class ThrottleTab(BasicTab):
    def __init__(self):
        super().__init__("Throttle / Drossel vor Intake-Plenum")
        grid = QGridLayout()

        box = QGroupBox("Throttle")
        f = QFormLayout(box)
        self.enabled = ConfigFieldFactory.check(True)
        self.diameter = ConfigFieldFactory.dspin(0.032, 0.0, 10.0, 0.001, 5)
        self.cd = ConfigFieldFactory.dspin(0.82, 0.0, 5.0, 0.01, 4)
        self.position = ConfigFieldFactory.dspin(0.65, 0.0, 1.0, 0.01, 4)
        self.position_mode = ConfigFieldFactory.combo(["fraction"], "fraction")
        self.A_max = ConfigFieldFactory.dspin(0.0, 0.0, 10.0, 0.00001, 8)
        self.T_upstream = ConfigFieldFactory.dspin(300.0, 0.0, 5000.0, 1.0, 2)
        self.p_upstream = ConfigFieldFactory.dspin(101325.0, 0.0, 1e9, 1000.0, 3)
        f.addRow("enabled", self.enabled)
        f.addRow("diameter_m", self.diameter)
        f.addRow("cd", self.cd)
        f.addRow("position", self.position)
        f.addRow("position_mode", self.position_mode)
        f.addRow("A_max_m2 (0=auto)", self.A_max)
        f.addRow("T_upstream_K", self.T_upstream)
        f.addRow("p_upstream_pa", self.p_upstream)

        info = QGroupBox("Info")
        vi = QVBoxLayout(info)
        vi.addWidget(QLabel(
            "Das Drosselmodell liegt vor dem Intake-Plenum.\n\n"
            "Massenstrom:\n"
            "- upstream reservoir -> throttle -> intake plenum\n\n"
            "Aktuell wird die effektive Fläche über\n"
            "- diameter_m\n"
            "- position\n"
            "- cd\n"
            "bestimmt."
        ))

        grid.addWidget(box, 0, 0)
        grid.addWidget(info, 0, 1)
        self.layout.addLayout(grid)

    def set_config(self, cfg: dict) -> None:
        th = cfg.get("throttle", {})
        self.enabled.setChecked(bool(th.get("enabled", True)))
        self.diameter.setValue(float(th.get("diameter_m", 0.032)))
        self.cd.setValue(float(th.get("cd", 0.82)))
        self.position.setValue(float(th.get("position", 0.65)))
        self.position_mode.setCurrentText(str(th.get("position_mode", "fraction")))
        self.A_max.setValue(float(th.get("A_max_m2", 0.0)))
        self.T_upstream.setValue(float(th.get("T_upstream_K", 300.0)))
        self.p_upstream.setValue(float(th.get("p_upstream_pa", 101325.0)))

    def update_config(self, cfg: dict) -> None:
        cfg["throttle"] = {
            "enabled": bool(self.enabled.isChecked()),
            "diameter_m": float(self.diameter.value()),
            "cd": float(self.cd.value()),
            "position": float(self.position.value()),
            "position_mode": self.position_mode.currentText(),
            "A_max_m2": float(self.A_max.value()),
            "T_upstream_K": float(self.T_upstream.value()),
            "p_upstream_pa": float(self.p_upstream.value()),
        }


class OutputTab(BasicTab):
    def __init__(self):
        super().__init__("Output / references / postprocess")
        grid = QGridLayout()
        box1 = QGroupBox("Output files")
        f1 = QFormLayout(box1)
        self.out_dir = ConfigFieldFactory.dir_line("out", dialog_title="Output-Ordner auswählen")
        self.csv_name = ConfigFieldFactory.line("out_gui.csv")
        self.plot_name = ConfigFieldFactory.line("out_gui.png")
        f1.addRow("out_dir", self.out_dir)
        f1.addRow("csv_name", self.csv_name)
        f1.addRow("plot_name", self.plot_name)

        box2 = QGroupBox("Angle reference")
        f2 = QFormLayout(box2)
        self.angle_ref = ConfigFieldFactory.combo(["FIRE_TDC", "GAS_EXCHANGE_TDC"], "FIRE_TDC")
        f2.addRow("mode", self.angle_ref)

        box3 = QGroupBox("Postprocess - slot events")
        f3 = QFormLayout(box3)
        self.se_enabled = ConfigFieldFactory.check(True)
        self.se_thr = ConfigFieldFactory.dspin(1e-7, 0.0, 1.0, 1e-7, 12)
        self.se_per_group = ConfigFieldFactory.check(True)
        self.se_per_group_blowdown = ConfigFieldFactory.check(True)
        self.se_plot_groups = ConfigFieldFactory.check(True)
        f3.addRow("enabled", self.se_enabled)
        f3.addRow("area_threshold_m2", self.se_thr)
        f3.addRow("per_group", self.se_per_group)
        f3.addRow("per_group_blowdown", self.se_per_group_blowdown)
        f3.addRow("plot_groups", self.se_plot_groups)

        box4 = QGroupBox("Postprocess - group contributions / flow model")
        f4 = QFormLayout(box4)
        self.gc_enabled = ConfigFieldFactory.check(True)
        self.gc_thr = ConfigFieldFactory.dspin(1e-7, 0.0, 1.0, 1e-7, 12)
        self.gf_enabled = ConfigFieldFactory.check(True)
        self.gf_mode = ConfigFieldFactory.combo(
            ["independent_nozzles_with_channel_losses", "independent_nozzles"],
            "independent_nozzles_with_channel_losses",
        )
        f4.addRow("group_contributions.enabled", self.gc_enabled)
        f4.addRow("group_contributions.threshold", self.gc_thr)
        f4.addRow("group_flow_model.enabled", self.gf_enabled)
        f4.addRow("group_flow_model.mode", self.gf_mode)

        grid.addWidget(box1, 0, 0)
        grid.addWidget(box2, 0, 1)
        grid.addWidget(box3, 1, 0)
        grid.addWidget(box4, 1, 1)
        self.layout.addLayout(grid)

    def set_config(self, cfg: dict) -> None:
        out = cfg["output_files"]
        ar = cfg["angle_reference"]
        pp = cfg["postprocess"]
        se = pp["slot_events"]
        gc = pp["group_contributions"]
        gf = pp["group_flow_model"]
        self.out_dir.setText(str(out.get("out_dir", "out")))
        self.csv_name.setText(str(out.get("csv_name", "out_gui.csv")))
        self.plot_name.setText(str(out.get("plot_name", "out_gui.png")))
        self.angle_ref.setCurrentText(str(ar.get("mode", "FIRE_TDC")))
        self.se_enabled.setChecked(bool(se.get("enabled", True)))
        self.se_thr.setValue(float(se.get("area_threshold_m2", 1e-7)))
        self.se_per_group.setChecked(bool(se.get("per_group", True)))
        self.se_per_group_blowdown.setChecked(bool(se.get("per_group_blowdown", True)))
        self.se_plot_groups.setChecked(bool(se.get("plot_groups", True)))
        self.gc_enabled.setChecked(bool(gc.get("enabled", True)))
        self.gc_thr.setValue(float(gc.get("area_threshold_m2", 1e-7)))
        self.gf_enabled.setChecked(bool(gf.get("enabled", True)))
        self.gf_mode.setCurrentText(str(gf.get("mode", "independent_nozzles_with_channel_losses")))

    def update_config(self, cfg: dict) -> None:
        cfg["output_files"] = {
            "out_dir": self.out_dir.text().strip(),
            "csv_name": self.csv_name.text().strip(),
            "plot_name": self.plot_name.text().strip(),
        }
        cfg["angle_reference"] = {"mode": self.angle_ref.currentText()}
        cfg["postprocess"] = {
            "slot_events": {
                "enabled": bool(self.se_enabled.isChecked()),
                "area_threshold_m2": float(self.se_thr.value()),
                "per_group": bool(self.se_per_group.isChecked()),
                "per_group_blowdown": bool(self.se_per_group_blowdown.isChecked()),
                "plot_groups": bool(self.se_plot_groups.isChecked()),
            },
            "group_contributions": {
                "enabled": bool(self.gc_enabled.isChecked()),
                "area_threshold_m2": float(self.gc_thr.value()),
            },
            "group_flow_model": {
                "enabled": bool(self.gf_enabled.isChecked()),
                "mode": self.gf_mode.currentText(),
            },
        }


class CsvPlotCanvas(QWidget):
    def __init__(self, empty_text: str = "Keine Daten"):
        super().__init__()
        self._empty_text = empty_text

        self._stack = QStackedWidget()

        self._message = QLabel(empty_text)
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        self._message.setMinimumHeight(340)
        self._message.setStyleSheet("border: 1px solid #cfd8e6; border-radius: 12px; background: #ffffff;")

        self._figure = Figure(constrained_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setMinimumHeight(340)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._stack.addWidget(self._message)
        self._stack.addWidget(self._canvas)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._stack)

        self.show_message(empty_text)

    def show_message(self, text: str) -> None:
        self._message.setText(text)
        self._figure.clear()
        self._canvas.draw_idle()
        self._stack.setCurrentWidget(self._message)

    def clear(self) -> None:
        self.show_message(self._empty_text)

    def plot_series(self, x, series_list, title: str, x_label: str, y_label: str = "") -> None:
        x_arr = np.asarray(x, dtype=float)
        if x_arr.size < 2 or not np.isfinite(x_arr).any():
            self.show_message("Keine gültigen x-Daten")
            return

        valid_series = []
        for y, name, color, style in series_list:
            arr = np.asarray(y, dtype=float)
            if arr.size == x_arr.size and np.isfinite(arr).any():
                valid_series.append((arr, name, color, style))

        if not valid_series:
            self.show_message("Keine Daten")
            return

        self._figure.clear()
        ax = self._figure.add_subplot(111)

        face = self.palette().window().color()
        text_color = self.palette().windowText().color()
        grid_color = QColor("#dbe3ef") if face.lightness() > 128 else QColor("#243041")
        self._figure.set_facecolor(face.name())
        ax.set_facecolor(face.name())

        for arr, name, color, style in valid_series:
            linestyle = '-' if style == 'solid' else '--'
            linewidth = 2.0 if style == 'solid' else 1.4
            ax.plot(x_arr, arr, label=name, linestyle=linestyle, linewidth=linewidth, color=color)

        ax.set_title(title, color=text_color.name())
        ax.set_xlabel(x_label, color=text_color.name())
        if y_label:
            ax.set_ylabel(y_label, color=text_color.name())
        ax.grid(True, alpha=0.35, color=grid_color.name())
        ax.tick_params(colors=text_color.name())
        for spine in ax.spines.values():
            spine.set_color(text_color.name())
        if len(valid_series) > 1:
            legend = ax.legend(loc='best')
            if legend is not None:
                legend.get_frame().set_alpha(0.9)

        self._stack.setCurrentWidget(self._canvas)
        self._canvas.draw_idle()


class ResultsTab(BasicTab):
    def __init__(self):
        super().__init__("Simulation results")
        self.last_out_dir: Path | None = None
        self._current_df = None
        self._numeric_columns: list[str] = []
        self._static_plot_pixmaps: dict[QLabel, QPixmap] = {}
        self._preview_labels: list[QLabel] = []
        self._csv_plot_labels: list[QLabel] = []
        self._preview_resize_timer = QTimer(self)
        self._preview_resize_timer.setSingleShot(True)
        self._preview_resize_timer.setInterval(40)
        self._preview_resize_timer.timeout.connect(self.resize_preview)
        self._preview_update_in_progress = False

        top = QHBoxLayout()
        self.btn_run = QPushButton("Simulation starten")
        self.btn_open_out = QPushButton("Output-Ordner öffnen")
        self.btn_refresh = QPushButton("Ansicht aktualisieren")
        top.addWidget(self.btn_run)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_open_out)
        top.addStretch(1)
        self.layout.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.layout.addWidget(self.progress)

        self.info = QLabel("Noch keine Simulation gestartet.")
        self.layout.addWidget(self.info)

        split = QSplitter(Qt.Horizontal)
        self._outer_splitter = split
        split.setChildrenCollapsible(False)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Erzeugte Dateien"))
        self.file_list = QListWidget()
        ll.addWidget(self.file_list)

        right = QWidget()
        rl = QVBoxLayout(right)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.setDocumentMode(True)

        self.tab_main_plot = QWidget()
        mpl = QVBoxLayout(self.tab_main_plot)
        self.main_plot_label = QLabel("Kein Hauptplot")
        self.main_plot_label.setAlignment(Qt.AlignCenter)
        self.main_plot_label.setMinimumHeight(340)
        self.main_plot_label.setStyleSheet("border: 1px solid #cfd8e6; border-radius: 12px; background: #ffffff;")
        mpl.addWidget(self.main_plot_label)

        self.tab_pv_plot = QWidget()
        pvl = QVBoxLayout(self.tab_pv_plot)
        self.pv_plot_label = QLabel("Kein p-V Plot")
        self.pv_plot_label.setAlignment(Qt.AlignCenter)
        self.pv_plot_label.setMinimumHeight(340)
        self.pv_plot_label.setStyleSheet("border: 1px solid #cfd8e6; border-radius: 12px; background: #ffffff;")
        pvl.addWidget(self.pv_plot_label)

        self.tab_p_t = QWidget()
        l1 = QVBoxLayout(self.tab_p_t)
        self.plot_p_t = CsvPlotCanvas("Kein CSV-Plot")
        l1.addWidget(self.plot_p_t)

        self.tab_p_theta = QWidget()
        l2 = QVBoxLayout(self.tab_p_theta)
        self.plot_p_theta = CsvPlotCanvas("Kein CSV-Plot")
        l2.addWidget(self.plot_p_theta)

        self.tab_v_theta = QWidget()
        l3 = QVBoxLayout(self.tab_v_theta)
        self.plot_v_theta = CsvPlotCanvas("Kein CSV-Plot")
        l3.addWidget(self.plot_v_theta)

        self.tab_area = QWidget()
        l4 = QVBoxLayout(self.tab_area)
        self.plot_area = CsvPlotCanvas("Kein CSV-Plot")
        l4.addWidget(self.plot_area)

        self.tab_mdot = QWidget()
        l5 = QVBoxLayout(self.tab_mdot)
        self.plot_mdot = CsvPlotCanvas("Kein CSV-Plot")
        l5.addWidget(self.plot_mdot)

        self.tab_explorer = QWidget()
        exl = QVBoxLayout(self.tab_explorer)

        explorer_top = QHBoxLayout()
        explorer_top.addWidget(QLabel("x-Achse"))
        self.x_axis_combo = QComboBox()
        explorer_top.addWidget(self.x_axis_combo, 1)
        self.rb_single = QRadioButton("single y")
        self.rb_multi = QRadioButton("multi y")
        self.rb_single.setChecked(True)
        explorer_top.addWidget(self.rb_single)
        explorer_top.addWidget(self.rb_multi)
        self.btn_apply_explorer = QPushButton("Explorer Plot aktualisieren")
        explorer_top.addWidget(self.btn_apply_explorer)
        exl.addLayout(explorer_top)

        explorer_mid = QSplitter(Qt.Horizontal)

        left_cols = QWidget()
        lcols = QVBoxLayout(left_cols)
        lcols.addWidget(QLabel("Verfügbare numerische Spalten"))
        self.available_columns = QListWidget()
        self.available_columns.setSelectionMode(QListWidget.ExtendedSelection)
        lcols.addWidget(self.available_columns)

        right_cols = QWidget()
        rcols = QVBoxLayout(right_cols)
        rcols.addWidget(QLabel("Gewählte y-Spalten"))
        self.selected_columns = QListWidget()
        self.selected_columns.setSelectionMode(QListWidget.ExtendedSelection)
        rcols.addWidget(self.selected_columns)

        btns = QHBoxLayout()
        self.btn_add_y = QPushButton("->")
        self.btn_remove_y = QPushButton("<-")
        self.btn_clear_y = QPushButton("Clear")
        btns.addWidget(self.btn_add_y)
        btns.addWidget(self.btn_remove_y)
        btns.addWidget(self.btn_clear_y)
        rcols.addLayout(btns)

        explorer_mid.addWidget(left_cols)
        explorer_mid.addWidget(right_cols)
        explorer_mid.setSizes([420, 420])
        exl.addWidget(explorer_mid)

        self.plot_explorer = CsvPlotCanvas("Noch kein Explorer-Plot")
        exl.addWidget(self.plot_explorer)

        self.tab_energy = QWidget()
        enl = QVBoxLayout(self.tab_energy)
        enl.addWidget(QLabel("Energy balance summary"))
        self.energy_summary_box = QPlainTextEdit()
        self.energy_summary_box.setReadOnly(True)
        self.energy_summary_box.setMinimumHeight(220)
        enl.addWidget(self.energy_summary_box)

        self.tab_csv = QWidget()
        csvl = QVBoxLayout(self.tab_csv)
        csvl.addWidget(QLabel("CSV-Kurzübersicht"))
        self.csv_summary = QTableWidget(0, 4)
        self.csv_summary.setHorizontalHeaderLabels(["Kennwert", "Spalte", "Wert", "Einheit/Info"])
        self.csv_summary.horizontalHeader().setStretchLastSection(True)
        self.csv_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.csv_summary.setAlternatingRowColors(True)
        csvl.addWidget(self.csv_summary)

        self.preview_tabs.addTab(self.tab_main_plot, "Hauptplot")
        self.preview_tabs.addTab(self.tab_pv_plot, "p-V Plot")
        self.preview_tabs.addTab(self.tab_p_t, "p(t)")
        self.preview_tabs.addTab(self.tab_p_theta, "p(θ)")
        self.preview_tabs.addTab(self.tab_v_theta, "V(θ)")
        self.preview_tabs.addTab(self.tab_area, "Flächen")
        self.preview_tabs.addTab(self.tab_mdot, "Massenströme")
        self.preview_tabs.addTab(self.tab_explorer, "Explorer")
        self.preview_tabs.addTab(self.tab_energy, "Energy Balance")
        self.preview_tabs.addTab(self.tab_csv, "CSV Summary")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(170)

        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QLabel("Log"))
        log_layout.addWidget(self.log, 1)

        self._right_splitter = QSplitter(Qt.Vertical)
        self._right_splitter.setChildrenCollapsible(False)
        self._right_splitter.addWidget(self.preview_tabs)
        self._right_splitter.addWidget(log_panel)
        self._right_splitter.setStretchFactor(0, 4)
        self._right_splitter.setStretchFactor(1, 1)
        self._right_splitter.setSizes([920, 220])
        rl.addWidget(self._right_splitter, 1)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([360, 1100])
        self.layout.addWidget(split, 1)

        self._preview_labels = [
            self.main_plot_label,
            self.pv_plot_label,
        ]
        self._csv_plot_widgets = [
            self.plot_p_t,
            self.plot_p_theta,
            self.plot_v_theta,
            self.plot_area,
            self.plot_mdot,
            self.plot_explorer,
        ]
        for label in self._preview_labels:
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.installEventFilter(self)
        for widget in self._csv_plot_widgets:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            widget.installEventFilter(self)
        self.preview_tabs.installEventFilter(self)
        self.tab_main_plot.installEventFilter(self)
        self.tab_pv_plot.installEventFilter(self)
        self.tab_p_t.installEventFilter(self)
        self.tab_p_theta.installEventFilter(self)
        self.tab_v_theta.installEventFilter(self)
        self.tab_area.installEventFilter(self)
        self.tab_mdot.installEventFilter(self)
        self.tab_explorer.installEventFilter(self)
        self._outer_splitter.installEventFilter(self)
        self._right_splitter.installEventFilter(self)
        self.preview_tabs.currentChanged.connect(lambda *_: self._schedule_preview_resize())

        self.btn_add_y.clicked.connect(self._add_selected_columns)
        self.btn_remove_y.clicked.connect(self._remove_selected_columns)
        self.btn_clear_y.clicked.connect(self._clear_selected_columns)
        self.btn_apply_explorer.clicked.connect(self._update_explorer_plot)
        self.available_columns.itemDoubleClicked.connect(lambda item: self._add_item_text_to_selected(item.text()))
        self.selected_columns.itemDoubleClicked.connect(lambda item: self.selected_columns.takeItem(self.selected_columns.row(item)))
        self.x_axis_combo.currentTextChanged.connect(self._update_explorer_plot)
        self.rb_single.toggled.connect(self._update_explorer_plot)
        self.rb_multi.toggled.connect(self._update_explorer_plot)

    def _set_image(self, label: QLabel, path: Path | None, empty_text: str) -> None:
        if path is None or not path.exists():
            self._static_plot_pixmaps.pop(label, None)
            label.setText(empty_text)
            label.setPixmap(QPixmap())
            return
        pm = QPixmap(str(path))
        if pm.isNull():
            self._static_plot_pixmaps.pop(label, None)
            label.setText(f"Plot konnte nicht geladen werden:\n{path.name}")
            label.setPixmap(QPixmap())
            return
        self._static_plot_pixmaps[label] = pm
        self._set_label_scaled_pixmap(label, pm)
        label.setText("")

    def _set_label_scaled_pixmap(self, label: QLabel, pm: QPixmap) -> None:
        if pm.isNull():
            label.setPixmap(QPixmap())
            return
        size = label.contentsRect().size()
        target_w = max(120, size.width() - 8)
        target_h = max(120, size.height() - 8)
        scaled = pm.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)
        label.setText("")

    def _schedule_preview_resize(self) -> None:
        self._preview_resize_timer.start()

    def _clear_selected_columns(self) -> None:
        self.selected_columns.clear()
        self._update_explorer_plot()

    def _add_item_text_to_selected(self, text: str) -> None:
        existing = [self.selected_columns.item(i).text() for i in range(self.selected_columns.count())]
        if text not in existing:
            self.selected_columns.addItem(text)
            self._update_explorer_plot()

    def _add_selected_columns(self) -> None:
        for item in self.available_columns.selectedItems():
            self._add_item_text_to_selected(item.text())

    def _remove_selected_columns(self) -> None:
        for item in self.selected_columns.selectedItems():
            self.selected_columns.takeItem(self.selected_columns.row(item))
        self._update_explorer_plot()

    def _render_xy_plot(self, x, series_list, title: str, x_label: str, widget: CsvPlotCanvas, y_label: str = "") -> None:
        widget.plot_series(x, series_list, title, x_label, y_label)

    def _fill_csv_summary(self, csv_path: Path | None) -> None:
        self.csv_summary.setRowCount(0)
        self._current_df = None
        self._numeric_columns = []
        self.available_columns.clear()
        self.selected_columns.clear()
        self.x_axis_combo.clear()
        if csv_path is None or not csv_path.exists():
            return
        try:
            df = pd.read_csv(csv_path)
            self._current_df = df
        except Exception as exc:
            self.csv_summary.setRowCount(1)
            vals = [("Fehler", "CSV", str(exc), "")]
            for r, row in enumerate(vals):
                for c, v in enumerate(row):
                    self.csv_summary.setItem(r, c, QTableWidgetItem(str(v)))
            return

        rows = []
        rows.append(("Zeilen", "rows", len(df), ""))
        rows.append(("Spalten", "columns", len(df.columns), ""))

        def add_if(col, stat, value, info=""):
            rows.append((stat, col, value, info))

        numeric_cols = list(df.select_dtypes(include="number").columns)
        self._numeric_columns = numeric_cols

        if "t_s" in df.columns:
            add_if("t_s", "t_min", float(df["t_s"].min()), "s")
            add_if("t_s", "t_max", float(df["t_s"].max()), "s")
        if "theta_deg" in df.columns:
            add_if("theta_deg", "theta_min", float(df["theta_deg"].min()), "deg KW")
            add_if("theta_deg", "theta_max", float(df["theta_deg"].max()), "deg KW")
        for col, unit in [("p_cyl_pa", "Pa"), ("T_cyl_K", "K"), ("V_m3", "m³"), ("x_m", "m"),
                          ("mdot_in_kg_s", "kg/s"), ("mdot_out_kg_s", "kg/s"),
                          ("A_in_m2", "m²"), ("A_ex_m2", "m²")]:
            if col in df.columns:
                add_if(col, "min", float(df[col].min()), unit)
                add_if(col, "max", float(df[col].max()), unit)

        extras = [c for c in numeric_cols if c not in {"t_s", "theta_deg", "p_cyl_pa", "T_cyl_K", "V_m3", "x_m", "mdot_in_kg_s", "mdot_out_kg_s", "A_in_m2", "A_ex_m2"}]
        for c in extras[:12]:
            add_if(c, "mean", float(df[c].mean()), "")

        # optional energy balance summary in output folder
        try:
            energy_path = None
            if self.last_out_dir is not None:
                cand = Path(self.last_out_dir) / "energy_balance_summary.json"
                if cand.exists():
                    energy_path = cand
            if energy_path is not None:
                ed = json.loads(energy_path.read_text(encoding="utf-8"))
                for k, v in ed.items():
                    unit = "%" if str(k).endswith("_pct") else "J"
                    rows.append(("Energy", k, v, unit))
        except Exception:
            pass

        self.csv_summary.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.csv_summary.setItem(r, c, QTableWidgetItem(str(v)))

        x_candidates = []
        if "theta_deg" in numeric_cols:
            x_candidates.append("theta_deg")
        if "t_s" in numeric_cols:
            x_candidates.append("t_s")
        for c in numeric_cols:
            if c not in x_candidates:
                x_candidates.append(c)

        self.x_axis_combo.addItems(x_candidates)
        for c in numeric_cols:
            self.available_columns.addItem(c)

        defaults = [c for c in ["p_cyl_pa", "V_m3"] if c in numeric_cols]
        for c in defaults:
            self._add_item_text_to_selected(c)

        self._update_csv_plot_tabs()
        self._update_explorer_plot()

    def _update_csv_plot_tabs(self) -> None:
        df = self._current_df
        if df is None or len(df) == 0:
            for lab in (self.plot_p_t, self.plot_p_theta, self.plot_v_theta, self.plot_area, self.plot_mdot, self.plot_explorer):
                lab.show_message("Keine CSV-Daten")
            return

        if "t_s" in df.columns and "p_cyl_pa" in df.columns:
            self._render_xy_plot(df["t_s"].to_numpy(), [(df["p_cyl_pa"].to_numpy(), "p_cyl", "#2563eb", "solid")], "Druck über Zeit", "t [s]", self.plot_p_t, "p [Pa]")
        else:
            self.plot_p_t.show_message("Spalten t_s / p_cyl_pa nicht vorhanden.")

        if "theta_deg" in df.columns and "p_cyl_pa" in df.columns:
            self._render_xy_plot(df["theta_deg"].to_numpy(), [(df["p_cyl_pa"].to_numpy(), "p_cyl", "#2563eb", "solid")], "Druck über Winkel", "θ [deg KW]", self.plot_p_theta, "p [Pa]")
        else:
            self.plot_p_theta.show_message("Spalten theta_deg / p_cyl_pa nicht vorhanden.")

        if "theta_deg" in df.columns and "V_m3" in df.columns:
            self._render_xy_plot(df["theta_deg"].to_numpy(), [(df["V_m3"].to_numpy(), "V", "#dc2626", "solid")], "Volumen über Winkel", "θ [deg KW]", self.plot_v_theta, "V [m³]")
        else:
            self.plot_v_theta.show_message("Spalten theta_deg / V_m3 nicht vorhanden.")

        if "theta_deg" in df.columns:
            area_series = []
            if "A_in_m2" in df.columns: area_series.append((df["A_in_m2"].to_numpy(), "A_in", "#2563eb", "solid"))
            if "A_ex_m2" in df.columns: area_series.append((df["A_ex_m2"].to_numpy(), "A_ex", "#dc2626", "solid"))
            if "lift_in_mm" in df.columns: area_series.append((df["lift_in_mm"].to_numpy(), "lift_in", "#0ea5e9", "dash"))
            if "lift_ex_mm" in df.columns: area_series.append((df["lift_ex_mm"].to_numpy(), "lift_ex", "#fb7185", "dash"))
            if area_series:
                self._render_xy_plot(df["theta_deg"].to_numpy(), area_series[:6], "Öffnungsflächen / Ventilhub", "θ [deg KW]", self.plot_area, "mixed")
            else:
                self.plot_area.show_message("Keine Flächen-/Hubspalten vorhanden.")
        else:
            self.plot_area.show_message("Spalte theta_deg nicht vorhanden.")

        if "t_s" in df.columns:
            mdot_series = []
            if "mdot_in_kg_s" in df.columns: mdot_series.append((df["mdot_in_kg_s"].to_numpy(), "mdot_in", "#2563eb", "solid"))
            if "mdot_out_kg_s" in df.columns: mdot_series.append((df["mdot_out_kg_s"].to_numpy(), "mdot_out", "#dc2626", "solid"))
            extra_mdot = [c for c in df.columns if c.endswith("_mdot_kg_s") and c not in {"mdot_in_kg_s", "mdot_out_kg_s"}]
            palette = ["#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b", "#84cc16", "#ec4899"]
            for i, c in enumerate(extra_mdot[:4]):
                mdot_series.append((df[c].to_numpy(), c.replace("_mdot_kg_s", ""), palette[i % len(palette)], "dash"))
            if mdot_series:
                self._render_xy_plot(df["t_s"].to_numpy(), mdot_series[:6], "Massenströme über Zeit", "t [s]", self.plot_mdot, "ṁ [kg/s]")
            else:
                self.plot_mdot.show_message("Keine Massenstromspalten vorhanden.")
        else:
            self.plot_mdot.show_message("Spalte t_s nicht vorhanden.")

    def _update_explorer_plot(self) -> None:
        df = self._current_df
        if df is None or len(df) == 0:
            self.plot_explorer.show_message("Keine CSV-Daten")
            return

        x_col = self.x_axis_combo.currentText().strip()
        if not x_col or x_col not in df.columns:
            self.plot_explorer.show_message("Bitte gültige x-Spalte wählen.")
            return

        selected = [self.selected_columns.item(i).text() for i in range(self.selected_columns.count())]
        selected = [c for c in selected if c in df.columns and c != x_col]
        if not selected:
            self.plot_explorer.show_message("Bitte mindestens eine y-Spalte wählen.")
            return

        palette = ["#2563eb", "#dc2626", "#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b", "#84cc16", "#ec4899"]
        series = []
        if self.rb_single.isChecked():
            selected = selected[:1]
        for i, c in enumerate(selected[:8]):
            series.append((df[c].to_numpy(), c, palette[i % len(palette)], "solid" if i < 2 else "dash"))

        self._render_xy_plot(df[x_col].to_numpy(), series, "Explorer Plot", x_col, self.plot_explorer, "selected y")

    def set_results(self, out_dir: Path, files: list[Path], log_text: str = "") -> None:
        self.last_out_dir = out_dir
        self.file_list.clear()
        for p in files:
            item = QListWidgetItem(p.name)
            item.setToolTip(str(p))
            self.file_list.addItem(item)
        self.log.setPlainText(log_text)
        self.info.setText(f"Output: {out_dir}")
        self.progress.setValue(100)

        main_png = None
        pv_png = None
        csv_path = None

        for p in files:
            if p.suffix.lower() == ".csv" and csv_path is None:
                csv_path = p
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                if p.stem.endswith("_pV"):
                    pv_png = p
                elif main_png is None:
                    main_png = p

        self._set_image(self.main_plot_label, main_png, "Kein Hauptplot gefunden.")
        self._set_image(self.pv_plot_label, pv_png, "Kein p-V Plot gefunden.")
        self._fill_csv_summary(csv_path)
        self._fill_energy_summary()


    def _fill_energy_summary(self) -> None:
        self.energy_summary_box.setPlainText("No energy balance summary found.")
        try:
            if self.last_out_dir is None:
                return
            p = Path(self.last_out_dir) / "energy_balance_summary.json"
            if not p.exists():
                return
            data = json.loads(p.read_text(encoding="utf-8"))
            lines = [
                f"E_flow_in_J           = {float(data.get('E_flow_in_J', 0.0)):.6g}",
                f"E_flow_out_J          = {float(data.get('E_flow_out_J', 0.0)):.6g}",
                f"E_piston_J            = {float(data.get('E_piston_J', 0.0)):.6g}",
                f"delta_U_J             = {float(data.get('delta_U_J', 0.0)):.6g}",
                f"closure_residual_J    = {float(data.get('closure_residual_J', 0.0)):.6g}",
                f"closure_relative_pct  = {float(data.get('closure_relative_pct', 0.0)):.6g}",
                "",
                f"U0_J                  = {float(data.get('U0_J', 0.0)):.6g}",
                f"U1_J                  = {float(data.get('U1_J', 0.0)):.6g}",
                "",
                "Interpretation:",
                "Residual near zero means the explicit open-system energy balance",
                "based on flow enthalpy, piston work and internal energy change",
                "closes well for the active cylinder.",
            ]
            self.energy_summary_box.setPlainText("\\n".join(lines))
        except Exception as exc:
            self.energy_summary_box.setPlainText(f"Energy summary could not be loaded:\\n{exc}")

    def resize_preview(self):
        if self._preview_update_in_progress:
            return
        self._preview_update_in_progress = True
        try:
            for label in (self.main_plot_label, self.pv_plot_label):
                pm = self._static_plot_pixmaps.get(label)
                if pm is not None and not pm.isNull():
                    self._set_label_scaled_pixmap(label, pm)
            if self._current_df is not None:
                self._update_csv_plot_tabs()
                self._update_explorer_plot()
        finally:
            self._preview_update_in_progress = False

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            if obj in self._preview_labels or obj in self._csv_plot_widgets or obj in {
                self.preview_tabs,
                self.tab_main_plot,
                self.tab_pv_plot,
                self.tab_p_t,
                self.tab_p_theta,
                self.tab_v_theta,
                self.tab_area,
                self.tab_mdot,
                self.tab_explorer,
                self._outer_splitter,
                self._right_splitter,
            }:
                self._schedule_preview_resize()
        return False

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        self._schedule_preview_resize()

    def showEvent(self, event):
        QWidget.showEvent(self, event)
        self._schedule_preview_resize()


class RawJsonTab(BasicTab):
    def __init__(self):
        super().__init__("Raw JSON")
        self.editor = QPlainTextEdit()
        self.layout.addWidget(self.editor)

    def set_config(self, cfg: dict) -> None:
        self.editor.setPlainText(json.dumps(cfg, indent=2))

    def get_json(self) -> dict:
        return json.loads(self.editor.toPlainText())




class EngineGraphDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Engine system graph", parent)
        self.graph = EngineSystemDiagramWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(self.graph)
        self.setWidget(scroll)
        self.node_click_callback = None
        self.graph.node_click_callback = self._node_clicked

    def _node_clicked(self, name):
        if self.node_click_callback:
            self.node_click_callback(name)

    def rebuild(self, cfg: dict):
        self.graph.set_config(cfg)



class TimingDiagramDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Timing diagram", parent)
        self.diagram = TimingDiagramWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(self.diagram)
        self.setWidget(scroll)

    def rebuild(self, cfg: dict):
        self.diagram.set_config(cfg)


class ConfigEditorWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MotorSim Config Editor v7.0")
        self.resize(1720, 1080)
        self.setDocumentMode(True)
        self.setDockOptions(
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.AnimatedDocks |
            QMainWindow.GroupedDragging
        )
        self.current_path: Path | None = None
        self.current_theme = 'light'
        self._config = normalize_config(get_default_config())
        self._ui_loading = False
        self._settings = QSettings("OpenAI", "MotorSimConfigEditor")

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.overview_tab = OverviewTab()
        self.inspector_tab = PropertyInspectorTab()
        self.engine_tab = EngineTab()
        self.gas_tab = GasTab()
        self.sim_tab = SimulationTab()
        self.gx_tab = GasExchangeTab()
        self.user_cylinder_tab = UserCylinderTab()
        self.plena_tab = PlenaTab()
        self.throttle_tab = ThrottleTab()
        self.output_tab = OutputTab()
        self.results_tab = ResultsTab()
        self.raw_tab = RawJsonTab()

        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.inspector_tab, "Inspector")
        self.tabs.addTab(self.engine_tab, "Engine")
        self.tabs.addTab(self.gas_tab, "Gas")
        self.tabs.addTab(self.sim_tab, "Simulation")
        self.tabs.addTab(self.gx_tab, "Gas exchange")
        self.tabs.addTab(self.user_cylinder_tab, "User cylinder")
        self.tabs.addTab(self.plena_tab, "Plena")
        self.tabs.addTab(self.throttle_tab, "Throttle")
        self.tabs.addTab(self.output_tab, "Output/Postprocess")
        self.tabs.addTab(self.results_tab, "Run/Results")
        self.tabs.addTab(self.raw_tab, "Raw JSON")
        self.setCentralWidget(self.tabs)

        self.project_dock = ProjectStructureDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        self.graph_dock = EngineGraphDock(self)
        self.graph_dock.node_click_callback = getattr(self, 'handle_graph_node', lambda *_args, **_kwargs: None)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.graph_dock)

        self.timing_dock = TimingDiagramDock(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.timing_dock)
        self.tabifyDockWidget(self.graph_dock, self.timing_dock)
        self.graph_dock.raise_()

        self.inspector_dock_tab = PropertyInspectorTab()
        self.inspector_dock = QDockWidget("Inspector", self)
        self.inspector_dock.setWidget(self.inspector_dock_tab)
        self.addDockWidget(Qt.RightDockWidgetArea, self.inspector_dock)

        self._build_actions()
        self._build_toolbar()
        self.setStatusBar(QStatusBar())
        self.overview_tab.set_jump_callback(getattr(self, 'goto_tab', lambda *_args, **_kwargs: None))
        self.inspector_tab.btn_sync.clicked.connect(self.sync_property_inspector)
        self.tabs.currentChanged.connect(lambda *_: self._update_status_context())

        self._bind_safe_callbacks()

        self.gx_tab.mode.currentTextChanged.connect(self._on_gx_mode_changed)
        self.gx_tab.preview_source.currentTextChanged.connect(self.refresh_preview)
        self.engine_tab.cycle_type.currentTextChanged.connect(self.refresh_preview)

        audit = self._startup_method_audit()
        restored_cfg = self._restore_persistent_ui_state()
        self.load_from_config(restored_cfg or self._config)
        try:
            missing = [k for k, v in audit.items() if not v]
            if missing:
                self.statusBar().showMessage('Startup audit missing: ' + ', '.join(missing), 8000)
        except Exception:
            pass

    def _startup_method_audit(self) -> dict:
        required = [
            "handle_graph_node",
            "_build_actions",
            "_build_toolbar",
            "goto_tab",
            "sync_property_inspector",
            "_bind_safe_callbacks",
            "load_from_config",
            "refresh_valve_preview",
            "_update_status_context",
        ]
        return {name: hasattr(self, name) for name in required}

    def _bind_safe_callbacks(self) -> None:
        try:
            self.gx_tab.valves.set_preview_callback(self.refresh_valve_preview)
        except Exception:
            pass
        try:
            self.gx_tab.slots.set_preview_callback(self.refresh_slot_preview)
        except Exception:
            pass
        try:
            self.user_cylinder_tab.set_assembly_callback(self.refresh_user_cylinder_assembly)
        except Exception:
            pass
        try:
            self.results_tab.btn_run.clicked.connect(self.run_simulation)
            self.results_tab.btn_refresh.clicked.connect(self.refresh_results_view)
            self.results_tab.btn_open_out.clicked.connect(self.open_output_dir)
            self.results_tab.file_list.itemDoubleClicked.connect(self.open_selected_result)
        except Exception:
            pass

    def _build_actions(self) -> None:
        self.act_new = QAction("Defaults", self)
        self.act_open = QAction("Load", self)
        self.act_save = QAction("Save", self)
        self.act_save_as = QAction("Save As", self)
        self.act_refresh_json = QAction("Forms -> JSON", self)
        self.act_apply_json = QAction("JSON -> Forms", self)
        self.act_validate = QAction("Validate", self)
        self.act_theme_light = QAction("Light theme", self)
        self.act_theme_dark = QAction("Dark theme", self)

        self.act_new.triggered.connect(self.reset_defaults)
        self.act_open.triggered.connect(self.load_file_dialog)
        self.act_save.triggered.connect(self.save_file)
        self.act_save_as.triggered.connect(lambda: self.save_file(save_as=True))
        self.act_refresh_json.triggered.connect(self.refresh_json_from_forms)
        self.act_apply_json.triggered.connect(self.apply_json_to_forms)
        self.act_validate.triggered.connect(self.validate_config)
        self.act_theme_light.triggered.connect(lambda: self.set_theme('light'))
        self.act_theme_dark.triggered.connect(lambda: self.set_theme('dark'))

        menu = self.menuBar().addMenu("File")
        menu.addAction(self.act_new)
        menu.addAction(self.act_open)
        menu.addAction(self.act_save)
        menu.addAction(self.act_save_as)

        tools = self.menuBar().addMenu("Tools")
        tools.addAction(self.act_refresh_json)
        tools.addAction(self.act_apply_json)
        tools.addAction(self.act_validate)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.project_dock.toggleViewAction())
        view_menu.addAction(self.graph_dock.toggleViewAction())
        view_menu.addAction(self.timing_dock.toggleViewAction())
        view_menu.addAction(self.inspector_dock.toggleViewAction())
        view_menu.addSeparator()
        act_raise_graph = QAction("Show engine system graph", self)
        act_raise_graph.triggered.connect(lambda: self._show_and_raise_dock(self.graph_dock))
        act_raise_timing = QAction("Show timing diagram", self)
        act_raise_timing.triggered.connect(lambda: self._show_and_raise_dock(self.timing_dock))
        view_menu.addAction(act_raise_graph)
        view_menu.addAction(act_raise_timing)

        theme_menu = self.menuBar().addMenu("Theme")
        theme_menu.addAction(self.act_theme_light)
        theme_menu.addAction(self.act_theme_dark)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)
        for act in (self.act_new, self.act_open, self.act_save, self.act_save_as, self.act_refresh_json, self.act_apply_json, self.act_validate):
            tb.addAction(act)

        tb.addSeparator()
        self.tab_jump = QComboBox()
        self.tab_jump.setMinimumWidth(180)
        for i in range(self.tabs.count()):
            self.tab_jump.addItem(self.tabs.tabText(i))
        self.tab_jump.currentTextChanged.connect(self.goto_tab)
        tb.addWidget(self.tab_jump)

        self.tab_search = QLineEdit()
        self.tab_search.setPlaceholderText("Find tab…")
        self.tab_search.setMaximumWidth(180)
        self.tab_search.returnPressed.connect(self.goto_matching_tab)
        tb.addWidget(self.tab_search)

        self.btn_refresh_all = QPushButton("Refresh all previews")
        self.btn_refresh_all.clicked.connect(self.refresh_all_views)
        tb.addWidget(self.btn_refresh_all)

        tb.addSeparator()
        for act in (self.act_theme_light, self.act_theme_dark):
            tb.addAction(act)

    def sync_property_inspector(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
            self.inspector_tab.rebuild(cfg)
            self.inspector_dock_tab.rebuild(cfg)
            self.inspector_dock_tab.rebuild(cfg)
        except Exception:
            pass

    def handle_graph_node(self, name: str):
        mapping = {
            "throttle": "Throttle",
            "int_plenum": "Plena",
            "ex_plenum": "Plena",
            "cylinders": "User cylinder",
            "source": "Throttle",
            "sink": "Gas exchange"
        }
        tab = mapping.get(name)
        if tab:
            self.goto_tab(tab)
        if name in ("cylinders", "sink"):
            self.timing_dock.raise_()

    def goto_tab(self, name: str) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == name:
                self.tabs.setCurrentIndex(i)
                self.tab_jump.setCurrentText(name)
                return

    def goto_matching_tab(self) -> None:
        query = self.tab_search.text().strip().lower()
        if not query:
            return
        for i in range(self.tabs.count()):
            if query in self.tabs.tabText(i).lower():
                self.tabs.setCurrentIndex(i)
                self.tab_jump.setCurrentText(self.tabs.tabText(i))
                return

    def _show_and_raise_dock(self, dock: QDockWidget) -> None:
        dock.show()
        dock.raise_()

    def _on_gx_mode_changed(self, *args) -> None:
        if self._ui_loading:
            return
        try:
            self.gx_tab._sync_mode_ui(self.gx_tab.mode.currentText())
        except Exception:
            pass
        self.refresh_preview()

    def _clear_inactive_preview_messages(self, selected: str) -> None:
        try:
            if selected != "valves":
                self.gx_tab.valves.preview.set_message("Valve preview inactive for current gas exchange mode.")
        except Exception:
            pass
        try:
            if selected != "slots":
                self.gx_tab.slots.preview.set_message("Slot preview inactive for current gas exchange mode.")
        except Exception:
            pass

    def refresh_ports_preview(self, *args) -> None:
        try:
            cfg = self.collect_config_from_forms()
            p = cfg.get("gasexchange", {}).get("ports", {})
            area_file = self._resolve_path(str(p.get("area_file", "")).strip())
            ak_file = self._resolve_path(str(p.get("alphak_file", "")).strip())
            self._clear_inactive_preview_messages("ports")
            self.timing_dock.rebuild(cfg)
            self.timing_dock.raise_()
            if not area_file.exists():
                self.statusBar().showMessage(f"Ports area file not found: {area_file}", 4000)
            elif str(p.get("alphak_file", "")).strip() and not ak_file.exists():
                self.statusBar().showMessage(f"Ports alphaK file not found: {ak_file}", 4000)
            else:
                self.statusBar().showMessage(f"Ports preview active in Timing dock: {area_file.name}", 3000)
        except Exception as exc:
            try:
                self.statusBar().showMessage(f"Ports preview warning: {exc}", 4000)
            except Exception:
                pass

    def refresh_preview(self, *args) -> None:
        if self._ui_loading:
            return
        source = self.gx_tab.preview_source.currentText()
        mode = self.gx_tab.mode.currentText()
        selected = mode if source == "auto" else source
        if selected == "slots":
            self.refresh_slot_preview()
        elif selected == "ports":
            self.refresh_ports_preview()
        else:
            self.refresh_valve_preview()

    def refresh_valve_preview(self, *args) -> None:
        try:
            cfg = self.collect_config_from_forms()
            self._clear_inactive_preview_messages('valves')
            cycle_deg = 720.0 if str(cfg["engine"]["cycle_type"]).upper() == "4T" else 360.0
            v = cfg["gasexchange"]["valves"]
            lift_file = self._resolve_path(v["lift_file"])
            ak_file = self._resolve_path(v["alphak_file"])
            if not lift_file.exists():
                self.gx_tab.valves.preview.set_message(f"Lift file not found: {lift_file}")
                return
            if not ak_file.exists():
                self.gx_tab.valves.preview.set_message(f"alphaK file not found: {ak_file}")
                return
            prof = ValveProfilesPeriodic.from_files(
                lift_file=str(lift_file),
                alphak_file=str(ak_file),
                intake_open=v["intake_open"],
                exhaust_open=v["exhaust_open"],
                scaling=v["scaling"],
                lift_angle_basis=v["lift_angle_basis"],
                cam_to_crank_ratio=v["cam_to_crank_ratio"],
                effective_lift_threshold_mm=v["effective_lift_threshold_mm"],
                cycle_deg=cycle_deg,
            )
            theta = np.linspace(0.0, cycle_deg, int(max(361, cycle_deg * 2 + 1)))
            lin = np.array([], dtype=float)
            lex = np.array([], dtype=float)
            ain = np.array([], dtype=float)
            aex = np.array([], dtype=float)
            lin = []
            lex = []
            ain = []
            aex = []
            for th in theta:
                li, le = prof.lifts_m(float(th))
                aki, ake = prof.alphak(float(th))
                lin.append(1e3 * li)
                lex.append(1e3 * le)
                ain.append(aki)
                aex.append(ake)
            lin = np.asarray(lin, dtype=float)
            lex = np.asarray(lex, dtype=float)
            ain = np.asarray(ain, dtype=float)
            aex = np.asarray(aex, dtype=float)

            thr = float(v["effective_lift_threshold_mm"])
            events = {}
            events.update(self._open_close_events(theta, lin, thr, "IVO_deg", "IVC_deg"))
            events.update(self._open_close_events(theta, lex, thr, "EVO_deg", "EVC_deg"))
            overlap_mask = (lin > thr) & (lex > thr)
            segs = self._segments_from_masks(theta, overlap_mask)
            if segs:
                overlap_deg = sum(max(0.0, b - a) for a, b in segs)
                events["OVERLAP_deg"] = float(overlap_deg)
            msg = f"°KW | timing/scaling active | basis={v['lift_angle_basis']}"
            self.gx_tab.valves.preview.set_valve_preview(theta, lin, lex, ain, aex, cycle_deg=cycle_deg, events=events, overlap_segments=segs, message=msg)
        except Exception as exc:
            self.gx_tab.valves.preview.set_message(f"Preview error: {exc}")

    def refresh_slot_preview(self, *args) -> None:
        try:
            cfg = self.collect_config_from_forms()
            self._clear_inactive_preview_messages('slots')
            cycle_deg = 720.0 if str(cfg["engine"]["cycle_type"]).upper() == "4T" else 360.0
            eng = cfg["engine"]
            slots = cfg["gasexchange"]["slots"]
            alpha_path = self._resolve_path(slots.get("alphak_file", ""))
            alpha = None
            if str(slots.get("alphak_file", "")).strip() and alpha_path.exists():
                alpha = AlphaK.from_file(str(alpha_path))

            kin = CrankSliderKinematics(
                bore_m=float(eng["bore_m"]),
                stroke_m=float(eng["stroke_m"]),
                conrod_m=float(eng["conrod_m"]),
                compression_ratio=float(eng["compression_ratio"]),
            )
            stroke = float(eng["stroke_m"])
            theta = np.linspace(0.0, cycle_deg, int(max(361, cycle_deg * 2 + 1)))

            intake_groups = slots.get("intake_groups") or ([slots.get("intake")] if slots.get("intake") else [])
            exhaust_groups = slots.get("exhaust_groups") or ([slots.get("exhaust")] if slots.get("exhaust") else [])

            intake_slot_geoms = [SlotGeom(float(g.get("width_m", 0.0)), float(g.get("height_m", 0.0)), int(g.get("count", 0)), float(g.get("offset_from_ut_m", 0.0)), dict(g.get("roof", {}) or {})) for g in intake_groups]
            exhaust_slot_geoms = [SlotGeom(float(g.get("width_m", 0.0)), float(g.get("height_m", 0.0)), int(g.get("count", 0)), float(g.get("offset_from_ut_m", 0.0)), dict(g.get("roof", {}) or {})) for g in exhaust_groups]

            area_in = []
            area_ex = []
            ak_in = []
            ak_ex = []

            for th in theta:
                th_rad = np.deg2rad(float(th))
                _, _, x = kin.volume_dVdtheta_x(th_rad)
                y_from_ut = max(0.0, stroke - float(x))
                Ain = sum(g.area_open(y_from_ut) for g in intake_slot_geoms)
                Aex = sum(g.area_open(y_from_ut) for g in exhaust_slot_geoms)
                area_in.append(Ain)
                area_ex.append(Aex)
                if alpha is not None:
                    ai, ae = alpha.eval(float(th))
                else:
                    ai, ae = 0.0, 0.0
                ak_in.append(ai)
                ak_ex.append(ae)

            area_in = np.asarray(area_in, dtype=float)
            area_ex = np.asarray(area_ex, dtype=float)
            ak_in = np.asarray(ak_in, dtype=float)
            ak_ex = np.asarray(ak_ex, dtype=float)

            thr = max(1e-12, 1e-5 * float(max(np.max(area_in) if area_in.size else 0.0, np.max(area_ex) if area_ex.size else 0.0, 1.0)))
            events = {}
            events.update(self._open_close_events(theta, area_in, thr, "INT_OPEN_deg", "INT_CLOSE_deg"))
            events.update(self._open_close_events(theta, area_ex, thr, "EXH_OPEN_deg", "EXH_CLOSE_deg"))
            overlap_mask = (area_in > thr) & (area_ex > thr)
            segs = self._segments_from_masks(theta, overlap_mask)
            if segs:
                events["OVERLAP_deg"] = float(sum(max(0.0, b - a) for a, b in segs))
            msg = "°KW | Schlitzsteuerung | Öffnungsflächen über Kurbelwinkel"
            self.gx_tab.slots.preview.set_slot_preview(theta, area_in, area_ex, ak_in, ak_ex, cycle_deg=cycle_deg, events=events, overlap_segments=segs, message=msg)
        except Exception as exc:
            self.gx_tab.slots.preview.set_message(f"Slot preview error: {exc}")

    def refresh_all_views(self) -> None:
        for fn in (
            self.refresh_preview,
            self.refresh_user_cylinder_assembly,
            self.refresh_results_view,
            self.sync_property_inspector,
            self._update_status_context,
        ):
            try:
                fn()
            except Exception:
                pass

    def build_diagnostic_report(self, cfg: dict) -> dict:
        errors, warnings, info = [], [], []

        eng = cfg.get("engine", {})
        rpm = float(eng.get("rpm", 0.0) or 0.0)
        freq = float(eng.get("freq_hz", 0.0) or 0.0)
        if rpm <= 0.0 and freq <= 0.0:
            errors.append("Neither RPM nor frequency is > 0.")
        if rpm > 0.0 and freq > 0.0:
            warnings.append("Both RPM and frequency are set. RPM currently dominates in the solver.")
        if float(eng.get("bore_m", 0.0) or 0.0) <= 0 or float(eng.get("stroke_m", 0.0) or 0.0) <= 0:
            errors.append("Bore and stroke must be > 0.")
        if float(eng.get("compression_ratio", 0.0) or 0.0) <= 1.0:
            errors.append("Compression ratio must be > 1.")

        gx = cfg.get("gasexchange", {})
        mode = str(gx.get("mode", "valves"))
        preview_source = str(gx.get("preview_source", "auto"))
        if preview_source not in ("auto", "valves", "ports", "slots"):
            warnings.append(f"Unknown preview source: {preview_source}")
        if mode == "valves":
            v = gx.get("valves", {})
            for key in ["lift_file", "alphak_file"]:
                p = self._resolve_path(str(v.get(key, "")).strip())
                if not p.exists():
                    warnings.append(f"Valve file not found: {p}")
        elif mode == "ports":
            p_cfg = gx.get("ports", {})
            for key in ["area_file", "alphak_file"]:
                p = self._resolve_path(str(p_cfg.get(key, "")).strip())
                if not p.exists():
                    warnings.append(f"Ports file not found: {p}")
        elif mode == "slots":
            info.append("Slots mode active. Check runner and plenum sizing carefully.")

        cyls = cfg.get("user_cylinders", [])
        enabled = [c for c in cyls if c.get("enabled", True)]
        if not cyls:
            errors.append("No user cylinders configured.")
        if not enabled:
            warnings.append("No enabled cylinders found. First cylinder will be used as fallback.")
        active = cfg.get("active_user_cylinder", "")
        if cyls and active not in [c.get("name") for c in cyls]:
            warnings.append("Active user cylinder name does not match list; builder will choose a fallback.")

        names = set()
        for c in cyls:
            name = str(c.get("name", "")).strip()
            if not name:
                errors.append("A user cylinder has an empty name.")
            if name in names:
                errors.append(f"Duplicate user cylinder name: {name}")
            names.add(name)

            rin = c.get("runners", {}).get("intake", {})
            rex = c.get("runners", {}).get("exhaust", {})
            for side_name, rr in [("intake", rin), ("exhaust", rex)]:
                if float(rr.get("diameter_m", 0.0) or 0.0) <= 0.0:
                    warnings.append(f"{name}: {side_name} runner diameter should be > 0.")
                if float(rr.get("volume_m3", 0.0) or 0.0) <= 0.0:
                    warnings.append(f"{name}: {side_name} runner volume should be > 0.")

        plena = cfg.get("plena", {})
        if float(plena.get("intake", {}).get("volume_m3", 0.0) or 0.0) <= 0.0:
            errors.append("Intake plenum volume must be > 0.")
        if float(plena.get("exhaust", {}).get("volume_m3", 0.0) or 0.0) <= 0.0:
            errors.append("Exhaust plenum volume must be > 0.")

        th = cfg.get("throttle", {})
        pos = float(th.get("position", 0.0) or 0.0)
        if th.get("enabled", False) and not (0.0 <= pos <= 1.0):
            warnings.append("Throttle position should be between 0 and 1 in fraction mode.")
        if th.get("enabled", False) and float(th.get("diameter_m", 0.0) or 0.0) <= 0.0 and float(th.get("A_max_m2", 0.0) or 0.0) <= 0.0:
            errors.append("Throttle requires diameter_m > 0 or A_max_m2 > 0.")

        out = cfg.get("output_files", {})
        if not str(out.get("csv_name", "")).strip().endswith(".csv"):
            warnings.append("CSV output filename does not end with .csv.")
        if not str(out.get("plot_name", "")).strip().lower().endswith((".png", ".jpg", ".jpeg")):
            warnings.append("Plot output filename is not an image extension.")

        info.append(f"Configured gas exchange mode: {mode}")
        info.append(f"Enabled cylinders: {len(enabled)}")
        return {"errors": errors, "warnings": warnings, "info": info}

    def reset_defaults(self) -> None:
        self.current_path = None
        self.load_from_config(normalize_config(get_default_config()))
        self.statusBar().showMessage("Default configuration loaded.", 4000)
        self._update_status_context()

    def refresh_user_cylinder_assembly(self, *args) -> None:
        try:
            cfg = self.collect_config_from_forms()
            active = cfg.get("active_user_cylinder", "")
            items = cfg.get("user_cylinders", [])
            current = next((it for it in items if it.get("name") == active), items[0] if items else {})
            self.user_cylinder_tab.assembly.set_data(cfg.get("engine", {}), current, cfg.get("gasexchange", {}))
        except Exception:
            pass

    def load_from_config(self, cfg: dict) -> None:
        cfg = normalize_config(cfg)
        self._config = cfg
        self._ui_loading = True
        try:
            self.engine_tab.set_config(cfg)
            self.gas_tab.set_config(cfg)
            self.sim_tab.set_config(cfg)
            self.gx_tab.set_config(cfg)
            self.user_cylinder_tab.set_config(cfg)
            self.plena_tab.set_config(cfg)
            self.throttle_tab.set_config(cfg)
            self.output_tab.set_config(cfg)
            self.raw_tab.set_config(cfg)
        finally:
            self._ui_loading = False
        self.refresh_all_views()
        self._save_persistent_ui_state()

    def collect_config_from_forms(self) -> dict:
        cfg = normalize_config(get_default_config())
        self.engine_tab.update_config(cfg)
        self.gas_tab.update_config(cfg)
        self.sim_tab.update_config(cfg)
        self.gx_tab.update_config(cfg)
        self.user_cylinder_tab.update_config(cfg)
        self.plena_tab.update_config(cfg)
        self.throttle_tab.update_config(cfg)
        self.output_tab.update_config(cfg)
        return normalize_config(cfg)

    def refresh_json_from_forms(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
            self.raw_tab.set_config(cfg)
            self.statusBar().showMessage("Raw JSON refreshed from form tabs.", 3000)
            try:
                self.sync_property_inspector()
            except Exception:
                pass
            try:
                self._update_status_context()
            except Exception:
                pass
        except Exception as exc:
            QMessageBox.critical(self, "Forms -> JSON", str(exc))

    def apply_json_to_forms(self) -> None:
        try:
            raw_text = self.raw_tab.editor.toPlainText() if hasattr(self.raw_tab, "editor") else self.raw_tab.text.toPlainText()
            cfg = json.loads(raw_text)
            cfg = normalize_config(cfg)
            self.load_from_config(cfg)
            self.statusBar().showMessage("JSON applied to form tabs.", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "JSON -> Forms", str(exc))

    def set_theme(self, theme: str) -> None:
        self.current_theme = str(theme).lower()
        app = QApplication.instance()
        if app is not None:
            apply_modern_style(app, self.current_theme)
        self._update_status_context()

    def _output_dir_from_cfg(self) -> Path:
        cfg = self.collect_config_from_forms()
        out_dir = Path(cfg["output_files"]["out_dir"])
        if not out_dir.is_absolute():
            if self.current_path is not None:
                out_dir = self.current_path.parent / out_dir
            else:
                out_dir = Path.cwd() / out_dir
        return out_dir

    def refresh_results_view(self) -> None:
        out_dir = self._output_dir_from_cfg()
        if not out_dir.exists():
            self.results_tab.info.setText(f"Output-Ordner existiert noch nicht: {out_dir}")
            self.results_tab.progress.setValue(0)
            self.results_tab.log.setPlainText("Noch keine Ergebnisse vorhanden.")
            return
        files = sorted([p for p in out_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower())
        self.results_tab.set_results(out_dir, files, self.results_tab.log.toPlainText())

    def open_output_dir(self) -> None:
        out_dir = self._output_dir_from_cfg()
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(out_dir))  # type: ignore[name-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(out_dir)])
            else:
                subprocess.Popen(["xdg-open", str(out_dir)])
        except Exception as exc:
            QMessageBox.warning(self, "Open output dir", f"Konnte Output-Ordner nicht öffnen:\n{exc}")

    def open_selected_result(self, item) -> None:
        out_dir = self._output_dir_from_cfg()
        path = out_dir / item.text()
        if not path.exists():
            return
        try:
            suf = path.suffix.lower()
            if suf in (".png", ".jpg", ".jpeg"):
                if path.stem.endswith("_pV"):
                    self.results_tab._set_image(self.results_tab.pv_plot_label, path, "Kein p-V Plot")
                    self.results_tab.preview_tabs.setCurrentWidget(self.results_tab.tab_pv_plot)
                else:
                    self.results_tab._set_image(self.results_tab.main_plot_label, path, "Kein Hauptplot")
                    self.results_tab.preview_tabs.setCurrentWidget(self.results_tab.tab_main_plot)
            elif suf == ".csv":
                self.results_tab._fill_csv_summary(path)
                self.results_tab.preview_tabs.setCurrentWidget(self.results_tab.tab_explorer)

            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[name-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            QMessageBox.warning(self, "Open result", f"Konnte Datei nicht öffnen:\n{exc}")

    def run_simulation(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
        except Exception as exc:
            QMessageBox.critical(self, "Simulation", f"Konfiguration ungültig:\n{exc}")
            return

        cfg_path = None
        if self.current_path is not None:
            cfg_path = self.current_path
        else:
            cfg_path = Path.cwd() / "config_gui_runtime.json"

        try:
            cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Simulation", f"Konfigurationsdatei konnte nicht geschrieben werden:\n{exc}")
            return

        self.results_tab.progress.setValue(10)
        self.results_tab.log.setPlainText("Simulation läuft...\n")
        self.tabs.setCurrentWidget(self.results_tab)
        QApplication.processEvents()

        run_script = (Path(__file__).resolve().parents[3] / "run.py")
        if not run_script.exists():
            # fallback: create a lightweight runner using module import
            code = (
                "import sys\n"
                "from pathlib import Path\n"
                "ROOT = Path(sys.argv[1]).resolve().parent\n"
                "SRC = ROOT / 'src'\n"
                "sys.path.insert(0, str(SRC))\n"
                "from motor_sim.main import run_case\n"
                "raise SystemExit(run_case(sys.argv[1]))\n"
            )
            temp_runner = cfg_path.parent / "_temp_run_case.py"
            temp_runner.write_text(code, encoding="utf-8")
            cmd = [sys.executable, str(temp_runner), str(cfg_path)]
        else:
            cmd = [sys.executable, str(run_script), str(cfg_path)]

        try:
            self.results_tab.progress.setValue(35)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(cfg_path.parent),
            )
            log_text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            self.results_tab.log.setPlainText(log_text.strip())
            self.results_tab.progress.setValue(80)

            out_dir = self._output_dir_from_cfg()
            files = sorted([p for p in out_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower()) if out_dir.exists() else []
            self.results_tab.set_results(out_dir, files, log_text.strip())

            if proc.returncode != 0:
                QMessageBox.warning(self, "Simulation", f"Simulation beendet mit Returncode {proc.returncode}.")
            else:
                self.statusBar().showMessage("Simulation erfolgreich abgeschlossen.", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Simulation", f"Simulation konnte nicht gestartet werden:\n{exc}")
            self.results_tab.progress.setValue(0)

    def _update_status_context(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
            mode = cfg["gasexchange"]["mode"]
            cycle = cfg["engine"]["cycle_type"]
            case = cfg.get("case_name", "")
            enabled = len([c for c in cfg.get("user_cylinders", []) if c.get("enabled", True)])
            self.statusBar().showMessage(f"Case: {case} | Cycle: {cycle} | Gas exchange: {mode} | Cyl: {enabled} | Theme: {self.current_theme}", 5000)
            report = self.build_diagnostic_report(cfg)
            self.overview_tab.update_summary(cfg, report)
            self.project_dock.rebuild(cfg)
            self.graph_dock.rebuild(cfg)
            self.timing_dock.rebuild(cfg)
            self.inspector_tab.rebuild(cfg)
            self.inspector_dock_tab.rebuild(cfg)
            if hasattr(self, "tab_jump"):
                self.tab_jump.setCurrentText(self.tabs.tabText(self.tabs.currentIndex()))
        except Exception:
            pass

    def validate_config(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
            json.dumps(cfg, indent=2)
            report = self.build_diagnostic_report(cfg)
        except Exception as exc:
            QMessageBox.critical(self, "Validation failed", str(exc))
            return
        self.overview_tab.update_summary(cfg, report)
        self.project_dock.rebuild(cfg)
        errs = report.get("errors", [])
        warns = report.get("warnings", [])
        if errs:
            QMessageBox.critical(self, "Validation failed", f"{len(errs)} error(s) found. See Overview tab.")
        elif warns:
            QMessageBox.warning(self, "Validation", f"No structural errors, but {len(warns)} warning(s) found. See Overview tab.")
        else:
            QMessageBox.information(self, "Validation", "Configuration looks good. See Overview tab for details.")

    def _resolve_path(self, text: str) -> Path:
        p = Path(text)
        if p.is_absolute():
            return p
        if self.current_path is not None:
            return self.current_path.parent / p
        return Path.cwd() / p

    @staticmethod
    def _segments_from_masks(theta: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
        segs = []
        if theta.size < 2:
            return segs
        start_idx = None
        for i, ok in enumerate(mask):
            if ok and start_idx is None:
                start_idx = i
            if (not ok) and start_idx is not None:
                segs.append((float(theta[start_idx]), float(theta[i - 1])))
                start_idx = None
        if start_idx is not None:
            segs.append((float(theta[start_idx]), float(theta[-1])))
        return segs

    @staticmethod
    def _open_close_events(theta: np.ndarray, y: np.ndarray, threshold: float, open_key: str, close_key: str) -> dict:
        out = {}
        mask = np.asarray(y, dtype=float) > float(threshold)
        idx = np.where(mask)[0]
        if idx.size:
            out[open_key] = float(theta[idx[0]])
            out[close_key] = float(theta[idx[-1]])
        return out

    def _save_persistent_ui_state(self) -> None:
        try:
            cfg = self.collect_config_from_forms()
        except Exception:
            cfg = None
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())
        self._settings.setValue("theme", self.current_theme)
        self._settings.setValue("currentTab", self.tabs.currentIndex())
        self._settings.setValue("currentPath", str(self.current_path) if self.current_path else "")
        self._settings.setValue("configSnapshot", json.dumps(cfg, indent=2) if cfg is not None else "")
        self._settings.sync()

    def _restore_persistent_ui_state(self) -> dict | None:
        restored_cfg = None
        try:
            saved_theme = str(self._settings.value("theme", self.current_theme) or self.current_theme)
            self.current_theme = saved_theme
            apply_modern_style(QApplication.instance() or QApplication([]), saved_theme)
        except Exception:
            pass
        try:
            saved_path = str(self._settings.value("currentPath", "") or "").strip()
            if saved_path:
                p = Path(saved_path)
                if p.exists():
                    self.current_path = p
                    restored_cfg = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            restored_cfg = None
        if restored_cfg is None:
            try:
                snapshot = str(self._settings.value("configSnapshot", "") or "").strip()
                if snapshot:
                    restored_cfg = json.loads(snapshot)
            except Exception:
                restored_cfg = None
        try:
            geom = self._settings.value("geometry")
            if geom is not None:
                self.restoreGeometry(geom)
        except Exception:
            pass
        try:
            state = self._settings.value("windowState")
            if state is not None:
                self.restoreState(state)
        except Exception:
            pass
        try:
            idx = int(self._settings.value("currentTab", 0) or 0)
            if 0 <= idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)
        except Exception:
            pass
        return restored_cfg

    def closeEvent(self, event) -> None:
        self._save_persistent_ui_state()
        super().closeEvent(event)

    def load_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load configuration", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        try:
            cfg = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", f"Could not load file:\n{exc}")
            return
        self.current_path = Path(path)
        self.load_from_config(cfg)
        self._save_persistent_ui_state()
        self.statusBar().showMessage(f"Loaded {path}", 4000)

    def save_file(self, save_as: bool = False) -> None:
        cfg = self.collect_config_from_forms()
        if save_as or self.current_path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save configuration", str(Path.cwd() / "config_gui.json"), "JSON (*.json)")
            if not path:
                return
            self.current_path = Path(path)
        try:
            self.current_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save file:\n{exc}")
            return
        self.raw_tab.set_config(cfg)
        self.statusBar().showMessage(f"Saved {self.current_path}", 4000)
        self.refresh_all_views()
        self._save_persistent_ui_state()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    apply_modern_style(app, "light")
    w = ConfigEditorWindow()
    if not w.isVisible():
        w.showMaximized()
    return app.exec()
