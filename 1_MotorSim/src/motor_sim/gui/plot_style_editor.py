from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from motor_sim.plot_config import dump_plot_style_yaml
from motor_sim.post.plotting import create_layout_figure, create_pv_figure

AVAILABLE_KEYS = [
    'p_cyl_bar', 'p_ref_compression_bar', 'p_ref_expansion_bar', 'V_cm3',
    'mdot_in_kg_s', 'mdot_out_kg_s', 'lift_in_mm', 'lift_ex_mm',
    'alphaK_in', 'alphaK_ex', 'alphaV_in', 'alphaV_ex',
    'A_in_mm2', 'A_ex_mm2', 'qdot_combustion_W', 'xb_combustion',
    'T_cyl_K', 'm_cyl_kg', 'V_m3', 'p_cyl_pa', 'A_in_m2', 'A_ex_m2',
]
COLOR_PRESETS = ['', 'tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'black', '0.35']
LINESTYLE_PRESETS = ['', '-', '--', ':', '-.']
LEGEND_LOCS = ['best', 'upper right', 'upper left', 'lower right', 'lower left', 'center right', 'center left']
INFO_BOX_LOCS = ['upper right', 'upper left', 'lower right', 'lower left', 'outside right upper', 'outside right lower']


class PlotStyleEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MotorSim Plot-Editor – Multi-Figure')
        self.resize(1840, 1000)

        self._updating_ui = False
        self._figure_models: list[dict] = []
        self._current_figure_index = -1
        self._current_plot_index = -1
        self._preview_df = None
        self._preview_meta = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        self.path_edit = QLineEdit(str(Path.cwd() / 'plot.yaml'))
        btn_open = QPushButton('Öffnen')
        btn_open.clicked.connect(self._open_yaml)
        btn_browse = QPushButton('Speichern unter …')
        btn_browse.clicked.connect(self._browse_save)
        btn_save = QPushButton('YAML speichern')
        btn_save.clicked.connect(self._save)
        top_bar.addWidget(QLabel('Datei:'))
        top_bar.addWidget(self.path_edit, 1)
        top_bar.addWidget(btn_open)
        top_bar.addWidget(btn_browse)
        top_bar.addWidget(btn_save)
        root.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Left: figures
        left = QWidget()
        left_lay = QVBoxLayout(left)
        fig_box = QGroupBox('Figures / Layouts')
        fig_lay = QVBoxLayout(fig_box)
        self.figure_list = QListWidget()
        self.figure_list.currentRowChanged.connect(self._on_figure_selected)
        fig_lay.addWidget(self.figure_list)
        fig_btns = QGridLayout()
        for i, (txt, cb) in enumerate([
            ('+ Figure', self._add_figure), ('Duplizieren', self._copy_figure),
            ('Löschen', self._del_figure), ('↑', lambda: self._move_figure(-1)),
            ('↓', lambda: self._move_figure(1)),
        ]):
            b = QPushButton(txt); b.clicked.connect(cb)
            fig_btns.addWidget(b, i // 2, i % 2)
        fig_lay.addLayout(fig_btns)
        left_lay.addWidget(fig_box)
        splitter.addWidget(left)

        # Center: figure + subplot editor
        center = QWidget()
        center_lay = QVBoxLayout(center)
        splitter.addWidget(center)

        self.figure_props = self._build_figure_props()
        center_lay.addWidget(self.figure_props)

        sub_split = QSplitter(Qt.Orientation.Horizontal)
        center_lay.addWidget(sub_split, 1)

        subplot_left = QWidget()
        subplot_left_lay = QVBoxLayout(subplot_left)
        plot_box = QGroupBox('Subplots der aktiven Figure')
        plot_lay = QVBoxLayout(plot_box)
        self.subplot_list = QListWidget()
        self.subplot_list.currentRowChanged.connect(self._on_subplot_selected)
        plot_lay.addWidget(self.subplot_list)
        plot_btns = QGridLayout()
        for i, (txt, cb) in enumerate([
            ('+ Plot', self._add_plot), ('Duplizieren', self._copy_plot),
            ('Löschen', self._del_plot), ('↑', lambda: self._move_plot(-1)),
            ('↓', lambda: self._move_plot(1)),
        ]):
            b = QPushButton(txt); b.clicked.connect(cb)
            plot_btns.addWidget(b, i // 2, i % 2)
        plot_lay.addLayout(plot_btns)
        subplot_left_lay.addWidget(plot_box)

        matrix_box = QGroupBox('Visuelle Layout-Matrix')
        matrix_lay = QVBoxLayout(matrix_box)
        matrix_lay.addWidget(QLabel('Doppelklick auf eine Zelle: gewählten Subplot an diese Position verschieben/tauschen.'))
        self.layout_matrix = QTableWidget(1, 1)
        self.layout_matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.layout_matrix.cellDoubleClicked.connect(self._matrix_swap_to)
        matrix_lay.addWidget(self.layout_matrix)
        subplot_left_lay.addWidget(matrix_box)
        sub_split.addWidget(subplot_left)

        subplot_editor = QWidget()
        subplot_editor_lay = QVBoxLayout(subplot_editor)
        subplot_editor_lay.addWidget(self._build_subplot_editor(), 1)
        sub_split.addWidget(subplot_editor)

        # Right: timing + live preview + YAML
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.addWidget(self._build_timing_box())
        right_lay.addWidget(self._build_preview_box(), 1)
        right_lay.addWidget(QLabel('YAML Vorschau'))
        self.yaml_preview = QPlainTextEdit()
        self.yaml_preview.setReadOnly(True)
        right_lay.addWidget(self.yaml_preview, 1)
        splitter.addWidget(right)
        splitter.setSizes([260, 1050, 700])

        self._seed_defaults()
        self._try_autoload_preview_data()
        self._refresh_preview()

    def _build_figure_props(self):
        box = QGroupBox('Figure-Einstellungen')
        lay = QGridLayout(box)
        self.fig_name = QLineEdit()
        self.fig_name.textChanged.connect(self._figure_changed)
        self.fig_suffix = QLineEdit()
        self.fig_suffix.textChanged.connect(self._figure_changed)
        self.rows = QSpinBox(); self.rows.setRange(1, 8); self.rows.valueChanged.connect(self._figure_changed)
        self.cols = QSpinBox(); self.cols.setRange(1, 8); self.cols.valueChanged.connect(self._figure_changed)
        self.fig_w = QDoubleSpinBox(); self.fig_w.setRange(2.0, 50.0); self.fig_w.setValue(13.0); self.fig_w.valueChanged.connect(self._figure_changed)
        self.fig_h = QDoubleSpinBox(); self.fig_h.setRange(2.0, 50.0); self.fig_h.setValue(12.0); self.fig_h.valueChanged.connect(self._figure_changed)
        self.dpi = QSpinBox(); self.dpi.setRange(60, 600); self.dpi.setValue(180); self.dpi.valueChanged.connect(self._figure_changed)
        self.title = QLineEdit(); self.title.textChanged.connect(self._figure_changed)
        self.sharex = QCheckBox('share x'); self.sharex.setChecked(True); self.sharex.toggled.connect(self._figure_changed)
        self.show_info = QCheckBox('Info-Box anzeigen'); self.show_info.setChecked(True); self.show_info.toggled.connect(self._figure_changed)
        self.auto_save = QCheckBox('Auto-Save mit Zeitstempel'); self.auto_save.toggled.connect(self._figure_changed)
        self.timestamp_dir = QLineEdit('timestamped_plots'); self.timestamp_dir.textChanged.connect(self._figure_changed)
        self.info_box_loc = QComboBox(); self.info_box_loc.addItems(INFO_BOX_LOCS); self.info_box_loc.currentTextChanged.connect(self._figure_changed)
        self.xtick_step = QDoubleSpinBox(); self.xtick_step.setRange(1.0, 720.0); self.xtick_step.setValue(180.0); self.xtick_step.valueChanged.connect(self._figure_changed)
        self.label_fontsize = QDoubleSpinBox(); self.label_fontsize.setRange(4.0, 30.0); self.label_fontsize.setValue(10.0); self.label_fontsize.valueChanged.connect(self._figure_changed)
        self.tick_labelsize = QDoubleSpinBox(); self.tick_labelsize.setRange(4.0, 30.0); self.tick_labelsize.setValue(9.0); self.tick_labelsize.valueChanged.connect(self._figure_changed)
        self.legend_fontsize = QDoubleSpinBox(); self.legend_fontsize.setRange(4.0, 30.0); self.legend_fontsize.setValue(8.0); self.legend_fontsize.valueChanged.connect(self._figure_changed)
        self.line_width = QDoubleSpinBox(); self.line_width.setRange(0.1, 10.0); self.line_width.setValue(1.5); self.line_width.valueChanged.connect(self._figure_changed)
        widgets = [
            ('Name', self.fig_name), ('Datei-Suffix', self.fig_suffix), ('Rows', self.rows), ('Cols', self.cols),
            ('Breite [in]', self.fig_w), ('Höhe [in]', self.fig_h), ('DPI', self.dpi), ('Titel', self.title),
            ('XTick-Schritt [deg]', self.xtick_step), ('Info-Box Position', self.info_box_loc),
            ('Label Font', self.label_fontsize), ('Tick Font', self.tick_labelsize),
            ('Legend Font', self.legend_fontsize), ('Linienbreite default', self.line_width),
            ('Timestamp-Ordner', self.timestamp_dir),
        ]
        for idx, (lab, widget) in enumerate(widgets):
            lay.addWidget(QLabel(lab), idx // 4, (idx % 4) * 2)
            lay.addWidget(widget, idx // 4, (idx % 4) * 2 + 1)
        lay.addWidget(self.sharex, 4, 0)
        lay.addWidget(self.show_info, 4, 1)
        lay.addWidget(self.auto_save, 4, 2, 1, 2)
        return box

    def _build_subplot_editor(self):
        box = QGroupBox('Subplot-Editor')
        lay = QVBoxLayout(box)
        head = QGridLayout()
        self.plot_title = QLineEdit(); self.plot_title.textChanged.connect(self._subplot_changed)
        self.plot_ylabel = QLineEdit(); self.plot_ylabel.textChanged.connect(self._subplot_changed)
        self.plot_y2label = QLineEdit(); self.plot_y2label.textChanged.connect(self._subplot_changed)
        self.plot_legend_loc = QComboBox(); self.plot_legend_loc.addItems(LEGEND_LOCS); self.plot_legend_loc.currentTextChanged.connect(self._subplot_changed)
        self.plot_ref_lines = QCheckBox('Referenzlinien'); self.plot_ref_lines.toggled.connect(self._subplot_changed)
        self.plot_shade_phases = QCheckBox('Phasen schattieren'); self.plot_shade_phases.toggled.connect(self._subplot_changed)
        self.plot_grid = QCheckBox('Grid'); self.plot_grid.setChecked(True); self.plot_grid.toggled.connect(self._subplot_changed)
        for idx, (lab, w) in enumerate([
            ('Titel', self.plot_title), ('Y1 Label', self.plot_ylabel), ('Y2 Label', self.plot_y2label), ('Legende', self.plot_legend_loc)
        ]):
            head.addWidget(QLabel(lab), 0, idx * 2)
            head.addWidget(w, 0, idx * 2 + 1)
        head.addWidget(self.plot_ref_lines, 1, 0)
        head.addWidget(self.plot_shade_phases, 1, 1)
        head.addWidget(self.plot_grid, 1, 2)
        lay.addLayout(head)

        lay.addWidget(QLabel('Y1-Serien'))
        self.primary_table = self._make_series_table()
        lay.addWidget(self.primary_table)
        btns1 = QHBoxLayout()
        for txt, cb in [('Signal(e) hinzufügen', lambda: self._select_from_dialog(self.primary_table, 'Y1')), ('Zeile löschen', lambda: self._delete_series_row(self.primary_table))]:
            b = QPushButton(txt); b.clicked.connect(cb); btns1.addWidget(b)
        lay.addLayout(btns1)

        lay.addWidget(QLabel('Y2-Serien'))
        self.secondary_table = self._make_series_table()
        lay.addWidget(self.secondary_table)
        btns2 = QHBoxLayout()
        for txt, cb in [('Signal(e) hinzufügen', lambda: self._select_from_dialog(self.secondary_table, 'Y2')), ('Zeile löschen', lambda: self._delete_series_row(self.secondary_table))]:
            b = QPushButton(txt); b.clicked.connect(cb); btns2.addWidget(b)
        lay.addLayout(btns2)
        return box

    def _make_series_table(self):
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(['Signal', 'Label', 'Farbe', 'Stil', 'Breite', 'Scale', 'Offset'])
        table.horizontalHeader().setStretchLastSection(True)
        table.itemChanged.connect(self._subplot_changed)
        return table

    def _build_timing_box(self):
        box = QGroupBox('Steuerzeiten-/Steuerkreis-Einstellungen')
        lay = QGridLayout(box)
        self.timing_cart_enabled = QCheckBox('Kartesisch aktiv'); self.timing_cart_enabled.setChecked(True); self.timing_cart_enabled.toggled.connect(self._refresh_preview)
        self.timing_polar_enabled = QCheckBox('Polar aktiv'); self.timing_polar_enabled.setChecked(True); self.timing_polar_enabled.toggled.connect(self._refresh_preview)
        self.timing_cart_auto = QCheckBox('Kartesisch Auto-Save'); self.timing_cart_auto.toggled.connect(self._refresh_preview)
        self.timing_polar_auto = QCheckBox('Polar Auto-Save'); self.timing_polar_auto.toggled.connect(self._refresh_preview)
        self.timing_cart_info = QComboBox(); self.timing_cart_info.addItems(INFO_BOX_LOCS); self.timing_cart_info.setCurrentText('outside right upper'); self.timing_cart_info.currentTextChanged.connect(self._refresh_preview)
        self.timing_dir = QLineEdit('timestamped_plots'); self.timing_dir.textChanged.connect(self._refresh_preview)
        lay.addWidget(self.timing_cart_enabled, 0, 0)
        lay.addWidget(self.timing_polar_enabled, 0, 1)
        lay.addWidget(self.timing_cart_auto, 1, 0)
        lay.addWidget(self.timing_polar_auto, 1, 1)
        lay.addWidget(QLabel('Kartesisch Info-Box'), 2, 0)
        lay.addWidget(self.timing_cart_info, 2, 1)
        lay.addWidget(QLabel('Timestamp-Ordner'), 3, 0)
        lay.addWidget(self.timing_dir, 3, 1)
        return box


    def _build_preview_box(self):
        box = QGroupBox('Live-Vorschau mit Matplotlib')
        lay = QVBoxLayout(box)

        top = QGridLayout()
        self.preview_path = QLineEdit(str((Path.cwd() / 'out' / 'out_gui.csv').resolve()))
        self.preview_path.textChanged.connect(self._preview_path_changed)
        btn_browse = QPushButton('CSV …')
        btn_browse.clicked.connect(self._browse_preview_csv)
        self.preview_auto = QCheckBox('Auto-Refresh')
        self.preview_auto.setChecked(True)
        self.preview_auto.toggled.connect(self._refresh_preview)
        btn_refresh = QPushButton('Vorschau aktualisieren')
        btn_refresh.clicked.connect(self._render_live_preview)
        self.preview_mode = QComboBox()
        self.preview_mode.addItems(['Aktive Figure', 'pV der aktiven Figure'])
        self.preview_mode.currentTextChanged.connect(self._refresh_preview)
        top.addWidget(QLabel('Preview-CSV'), 0, 0)
        top.addWidget(self.preview_path, 0, 1)
        top.addWidget(btn_browse, 0, 2)
        top.addWidget(self.preview_auto, 1, 0)
        top.addWidget(btn_refresh, 1, 1)
        top.addWidget(self.preview_mode, 1, 2)
        lay.addLayout(top)

        self.preview_status = QLabel('Noch keine Vorschau geladen.')
        self.preview_status.setWordWrap(True)
        lay.addWidget(self.preview_status)

        self.preview_tabs = QTabWidget()
        self.preview_canvas_main = FigureCanvas(create_layout_figure(self._build_preview_dataframe(), {'plots': [], 'rows':1, 'cols':1, 'title':'Leer'}, cycle_deg=720.0, angle_ref_mode='FIRE_TDC'))
        self.preview_toolbar_main = NavigationToolbar(self.preview_canvas_main, self)
        page_main = QWidget(); page_main_lay = QVBoxLayout(page_main); page_main_lay.addWidget(self.preview_toolbar_main); page_main_lay.addWidget(self.preview_canvas_main, 1)
        self.preview_tabs.addTab(page_main, 'Layout')

        self.preview_canvas_pv = FigureCanvas(create_layout_figure(self._build_preview_dataframe(), {'plots': [], 'rows':1, 'cols':1, 'title':'Leer'}, cycle_deg=720.0, angle_ref_mode='FIRE_TDC'))
        self.preview_toolbar_pv = NavigationToolbar(self.preview_canvas_pv, self)
        page_pv = QWidget(); page_pv_lay = QVBoxLayout(page_pv); page_pv_lay.addWidget(self.preview_toolbar_pv); page_pv_lay.addWidget(self.preview_canvas_pv, 1)
        self.preview_tabs.addTab(page_pv, 'pV')
        lay.addWidget(self.preview_tabs, 1)
        return box

    def _browse_preview_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Preview-CSV öffnen', self.preview_path.text(), 'CSV (*.csv);;Alle Dateien (*)')
        if path:
            self.preview_path.setText(path)
            self._try_autoload_preview_data()
            self._render_live_preview()

    def _preview_path_changed(self, *_):
        if self.preview_auto.isChecked():
            self._try_autoload_preview_data()

    def _try_autoload_preview_data(self):
        path = Path(self.preview_path.text().strip()) if self.preview_path.text().strip() else None
        if path and path.exists():
            try:
                self._preview_df = pd.read_csv(path)
                self._preview_meta = {'source': str(path.resolve())}
                self.preview_status.setText(f'Preview-Daten geladen: {path.name} ({len(self._preview_df)} Zeilen)')
                return
            except Exception as exc:
                self.preview_status.setText(f'Preview-CSV konnte nicht geladen werden. Fallback auf Demo-Daten. Fehler: {exc}')
        self._preview_df = self._build_preview_dataframe()
        self._preview_meta = {'source': 'demo'}
        self.preview_status.setText('Preview läuft mit internen Demo-Daten. Für echte Daten eine CSV aus out/ auswählen.')

    def _build_preview_dataframe(self):
        theta = np.linspace(-360.0, 360.0, 721)
        rad = np.deg2rad(theta)
        phase_bounds = [(-360, -180, 'ansaugen'), (-180, 0, 'verdichten'), (0, 180, 'arbeiten'), (180, 360, 'ausschieben')]
        ideal_phase = np.empty(theta.shape, dtype=object)
        for a, b, name in phase_bounds:
            mask = (theta >= a) & (theta < b if b < 360 else theta <= b)
            ideal_phase[mask] = name
        V_m3 = 2.3e-4 + 1.6e-4 * (1.0 - np.cos(rad)) / 2.0
        p_cyl_pa = 1.2e5 + 4.0e6 * np.exp(-((theta - 10.0) / 34.0) ** 2) + 4.5e5 * (1.0 - np.cos(rad + 0.15))
        p_ref_compression_pa = 1.1e5 + 1.8e6 * np.maximum(0.0, np.cos(np.deg2rad(theta + 25.0))) ** 2.1
        p_ref_expansion_pa = 1.05e5 + 1.3e6 * np.maximum(0.0, np.cos(np.deg2rad(theta - 20.0))) ** 1.7
        lift_in_mm = 8.0 * np.maximum(0.0, np.sin(np.deg2rad(theta + 145.0))) ** 1.6
        lift_ex_mm = 7.0 * np.maximum(0.0, np.sin(np.deg2rad(theta - 125.0))) ** 1.7
        alphaK_in = np.clip(lift_in_mm / 8.0, 0.0, 1.0)
        alphaK_ex = np.clip(lift_ex_mm / 7.0, 0.0, 1.0)
        alphaV_in = np.sqrt(alphaK_in)
        alphaV_ex = np.sqrt(alphaK_ex)
        A_in_m2 = 2.2e-4 * alphaK_in
        A_ex_m2 = 1.8e-4 * alphaK_ex
        mdot_in_kg_s = 0.018 * np.maximum(0.0, np.sin(np.deg2rad(theta + 140.0)))
        mdot_out_kg_s = 0.022 * np.maximum(0.0, np.sin(np.deg2rad(theta - 135.0)))
        qdot_combustion_W = 1.4e5 * np.exp(-((theta - 5.0) / 18.0) ** 2)
        xb_combustion = 1.0 / (1.0 + np.exp(-(theta - 5.0) / 10.0))
        T_cyl_K = 300.0 + 1450.0 * np.exp(-((theta - 15.0) / 45.0) ** 2) + 150.0 * (1.0 - np.cos(rad))
        m_cyl_kg = 3.4e-4 + 0.7e-4 * np.sin(np.deg2rad(theta + 70.0))
        cycle_index = np.zeros_like(theta, dtype=int)
        return pd.DataFrame({
            'theta_deg': theta,
            'ideal_phase': ideal_phase,
            'V_m3': V_m3,
            'p_cyl_pa': p_cyl_pa,
            'p_ref_compression_pa': p_ref_compression_pa,
            'p_ref_expansion_pa': p_ref_expansion_pa,
            'lift_in_mm': lift_in_mm,
            'lift_ex_mm': lift_ex_mm,
            'alphaK_in': alphaK_in,
            'alphaK_ex': alphaK_ex,
            'alphaV_in': alphaV_in,
            'alphaV_ex': alphaV_ex,
            'A_in_m2': A_in_m2,
            'A_ex_m2': A_ex_m2,
            'mdot_in_kg_s': mdot_in_kg_s,
            'mdot_out_kg_s': mdot_out_kg_s,
            'qdot_combustion_W': qdot_combustion_W,
            'xb_combustion': xb_combustion,
            'T_cyl_K': T_cyl_K,
            'm_cyl_kg': m_cyl_kg,
            'cycle_index': cycle_index,
        })

    def _draw_on_canvas(self, canvas: FigureCanvas, fig):
        old_fig = canvas.figure
        canvas.figure = fig
        try:
            canvas.draw_idle()
        finally:
            if old_fig is not None and old_fig is not fig:
                try:
                    import matplotlib.pyplot as plt
                    plt.close(old_fig)
                except Exception:
                    pass

    def _render_live_preview(self, *_):
        if self._preview_df is None:
            self._try_autoload_preview_data()
        fig_cfg = self._get_current_figure()
        if fig_cfg is None:
            self.preview_status.setText('Keine aktive Figure gewählt.')
            return
        try:
            df = self._preview_df if self._preview_df is not None else self._build_preview_dataframe()
            layout_fig = create_layout_figure(
                df=df,
                fig_cfg=deepcopy(fig_cfg),
                cycle_deg=720.0,
                angle_ref_mode='FIRE_TDC',
                valve_events={'IVO_deg': -10.0, 'IVC_deg': 210.0, 'EVO_deg': 130.0, 'EVC_deg': 360.0},
                timing_validation={'timing_plausible': True},
                closed_cycle_summary={'compression': {'n_polytropic': 1.31}, 'expansion': {'n_polytropic': 1.24}},
                crank_angle_offset_deg=0.0,
            )
            self._draw_on_canvas(self.preview_canvas_main, layout_fig)
            pv_fig = create_pv_figure(df, deepcopy(fig_cfg))
            if pv_fig is None:
                pv_fig = create_layout_figure(df=df, fig_cfg={'plots': [], 'rows':1, 'cols':1, 'title':'Kein pV-Plot aktiviert'}, cycle_deg=720.0, angle_ref_mode='FIRE_TDC')
            self._draw_on_canvas(self.preview_canvas_pv, pv_fig)
            source = self._preview_meta.get('source', 'unbekannt')
            self.preview_status.setText(f'Live-Vorschau aktualisiert. Quelle: {source}')
            if self.preview_mode.currentText() == 'pV der aktiven Figure':
                self.preview_tabs.setCurrentIndex(1)
            else:
                self.preview_tabs.setCurrentIndex(0)
        except Exception as exc:
            self.preview_status.setText(f'Vorschau-Fehler: {exc}')

    def _seed_defaults(self):
        self._figure_models = [
            {
                'name': 'Hauptlayout', 'file_suffix': '', 'figsize_in': [13.0, 12.0], 'dpi': 180,
                'title': 'MotorSim – gespeicherte Zyklen', 'label_fontsize': 10.0, 'tick_labelsize': 9.0,
                'legend_fontsize': 8.0, 'line_width': 1.5, 'rows': 2, 'cols': 2, 'sharex': True,
                'xtick_step_deg': 180.0, 'show_info_box': True, 'info_box_loc': 'upper right',
                'auto_save_timestamped': False, 'timestamp_dir': 'timestamped_plots',
                'plots': [
                    {'title': 'Druck', 'ylabel': 'p [bar]', 'y2label': '', 'legend_loc': 'upper right', 'shade_phases': True, 'reference_lines': True, 'grid': True,
                     'series': [{'key': 'p_cyl_bar', 'label': 'p_cyl', 'color': 'tab:blue'}], 'secondary_series': []},
                    {'title': 'Volumen / Hub', 'ylabel': 'V [cm³]', 'y2label': 'Hub [mm]', 'legend_loc': 'upper right', 'shade_phases': True, 'reference_lines': True, 'grid': True,
                     'series': [{'key': 'V_cm3', 'label': 'V', 'color': 'tab:purple', 'linestyle': '--'}], 'secondary_series': [{'key': 'lift_in_mm', 'label': 'Einlass', 'color': 'tab:red'}, {'key': 'lift_ex_mm', 'label': 'Auslass', 'color': 'tab:brown'}]},
                    {'title': 'Massenstrom', 'ylabel': 'ṁ [kg/s]', 'y2label': '', 'legend_loc': 'upper right', 'shade_phases': True, 'reference_lines': True, 'grid': True,
                     'series': [{'key': 'mdot_in_kg_s', 'label': 'ṁ_in', 'color': 'tab:blue'}, {'key': 'mdot_out_kg_s', 'label': 'ṁ_out', 'color': 'tab:orange'}], 'secondary_series': []},
                    {'title': 'Verbrennung', 'ylabel': 'Q̇ [W]', 'y2label': 'x_b [-]', 'legend_loc': 'upper right', 'shade_phases': True, 'reference_lines': True, 'grid': True,
                     'series': [{'key': 'qdot_combustion_W', 'label': 'Q̇', 'color': 'tab:blue'}], 'secondary_series': [{'key': 'xb_combustion', 'label': 'x_b', 'color': 'tab:orange', 'linestyle': '--'}]},
                ]
            }
        ]
        self._refresh_figure_list(0)
        self._refresh_preview()

    def _open_yaml(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Plot-Datei öffnen', self.path_edit.text(), 'Plot Dateien (*.yaml *.yml *.json)')
        if path:
            self.path_edit.setText(path)
            self._load_config_from_file(Path(path))

    def _browse_save(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Plot YAML speichern', self.path_edit.text(), 'YAML (*.yaml *.yml)')
        if path:
            self.path_edit.setText(path)

    def _load_config_from_file(self, path: Path):
        text = path.read_text(encoding='utf-8')
        if path.suffix.lower() in {'.yaml', '.yml'}:
            if yaml is None:
                raise RuntimeError('PyYAML ist nicht installiert.')
            cfg = yaml.safe_load(text) or {}
        else:
            import json
            cfg = json.loads(text)
        if not isinstance(cfg, dict):
            raise ValueError('Ungültige Plot-Konfiguration.')

        self._figure_models = [dict(f) for f in (cfg.get('figures', []) or []) if isinstance(f, dict)]
        if not self._figure_models and isinstance(cfg.get('main_plot'), dict):
            self._figure_models = [dict(cfg['main_plot'])]
        if not self._figure_models:
            self._seed_defaults(); return

        timing = cfg.get('timing_plots', {}) or {}
        cart = timing.get('cartesian', {}) or {}
        polar = timing.get('polar', {}) or {}
        self.timing_cart_enabled.setChecked(bool(cart.get('enabled', True)))
        self.timing_polar_enabled.setChecked(bool(polar.get('enabled', True)))
        self.timing_cart_auto.setChecked(bool(cart.get('auto_save_timestamped', False)))
        self.timing_polar_auto.setChecked(bool(polar.get('auto_save_timestamped', False)))
        self.timing_cart_info.setCurrentText(str(cart.get('info_box_loc', 'outside right upper')))
        self.timing_dir.setText(str(cart.get('timestamp_dir', polar.get('timestamp_dir', 'timestamped_plots'))))
        self._refresh_figure_list(0)
        self._refresh_preview()

    def _refresh_figure_list(self, select_row=0):
        self._updating_ui = True
        self.figure_list.clear()
        for i, fig in enumerate(self._figure_models, start=1):
            QListWidgetItem(f'{i:02d} – {fig.get("name", f"Figure {i}")}', self.figure_list)
        self._updating_ui = False
        if self._figure_models:
            self.figure_list.setCurrentRow(max(0, min(select_row, len(self._figure_models) - 1)))

    def _on_figure_selected(self, row: int):
        if self._updating_ui:
            return
        self._store_current_subplot()
        self._store_current_figure()
        self._current_figure_index = row
        self._current_plot_index = -1
        if row < 0 or row >= len(self._figure_models):
            return
        fig = self._figure_models[row]
        self._updating_ui = True
        self.fig_name.setText(str(fig.get('name', '')))
        self.fig_suffix.setText(str(fig.get('file_suffix', '')))
        self.rows.setValue(int(fig.get('rows', 1) or 1))
        self.cols.setValue(int(fig.get('cols', 1) or 1))
        fs = list(fig.get('figsize_in', [13.0, 12.0]))
        self.fig_w.setValue(float(fs[0] if len(fs) > 0 else 13.0))
        self.fig_h.setValue(float(fs[1] if len(fs) > 1 else 12.0))
        self.dpi.setValue(int(fig.get('dpi', 180) or 180))
        self.title.setText(str(fig.get('title', '')))
        self.sharex.setChecked(bool(fig.get('sharex', True)))
        self.show_info.setChecked(bool(fig.get('show_info_box', True)))
        self.auto_save.setChecked(bool(fig.get('auto_save_timestamped', False)))
        self.timestamp_dir.setText(str(fig.get('timestamp_dir', 'timestamped_plots')))
        self.info_box_loc.setCurrentText(str(fig.get('info_box_loc', 'upper right')))
        self.xtick_step.setValue(float(fig.get('xtick_step_deg', 180.0) or 180.0))
        self.label_fontsize.setValue(float(fig.get('label_fontsize', 10.0) or 10.0))
        self.tick_labelsize.setValue(float(fig.get('tick_labelsize', 9.0) or 9.0))
        self.legend_fontsize.setValue(float(fig.get('legend_fontsize', 8.0) or 8.0))
        self.line_width.setValue(float(fig.get('line_width', 1.5) or 1.5))
        self._updating_ui = False
        self._refresh_subplot_list(0)
        self._refresh_layout_matrix()
        self._refresh_preview()

    def _store_current_figure(self):
        idx = self._current_figure_index
        if self._updating_ui or idx < 0 or idx >= len(self._figure_models):
            return
        fig = self._figure_models[idx]
        fig['name'] = self.fig_name.text().strip() or f'Figure {idx+1}'
        fig['file_suffix'] = self.fig_suffix.text().strip()
        fig['rows'] = self.rows.value()
        fig['cols'] = self.cols.value()
        fig['figsize_in'] = [self.fig_w.value(), self.fig_h.value()]
        fig['dpi'] = self.dpi.value()
        fig['title'] = self.title.text().strip()
        fig['sharex'] = self.sharex.isChecked()
        fig['show_info_box'] = self.show_info.isChecked()
        fig['auto_save_timestamped'] = self.auto_save.isChecked()
        fig['timestamp_dir'] = self.timestamp_dir.text().strip() or 'timestamped_plots'
        fig['info_box_loc'] = self.info_box_loc.currentText().strip() or 'upper right'
        fig['xtick_step_deg'] = self.xtick_step.value()
        fig['label_fontsize'] = self.label_fontsize.value()
        fig['tick_labelsize'] = self.tick_labelsize.value()
        fig['legend_fontsize'] = self.legend_fontsize.value()
        fig['line_width'] = self.line_width.value()
        item = self.figure_list.item(idx)
        if item is not None:
            item.setText(f'{idx+1:02d} – {fig["name"]}')

    def _figure_changed(self, *_):
        if self._updating_ui:
            return
        self._store_current_figure()
        self._refresh_layout_matrix()
        self._refresh_preview()

    def _refresh_subplot_list(self, select_row=0):
        self._updating_ui = True
        self.subplot_list.clear()
        fig = self._get_current_figure()
        if fig is not None:
            for i, plot in enumerate(fig.get('plots', []), start=1):
                QListWidgetItem(f'{i:02d} – {plot.get("title", f"Plot {i}")}', self.subplot_list)
        self._updating_ui = False
        if fig and fig.get('plots'):
            self.subplot_list.setCurrentRow(max(0, min(select_row, len(fig['plots']) - 1)))
        else:
            self._clear_subplot_editor()

    def _get_current_figure(self):
        idx = self._current_figure_index
        if 0 <= idx < len(self._figure_models):
            return self._figure_models[idx]
        return None

    def _on_subplot_selected(self, row: int):
        if self._updating_ui:
            return
        self._store_current_subplot()
        self._current_plot_index = row
        fig = self._get_current_figure()
        if fig is None or row < 0 or row >= len(fig.get('plots', [])):
            self._clear_subplot_editor(); return
        plot = fig['plots'][row]
        self._updating_ui = True
        self.plot_title.setText(str(plot.get('title', '')))
        self.plot_ylabel.setText(str(plot.get('ylabel', '')))
        self.plot_y2label.setText(str(plot.get('y2label', '')))
        self.plot_legend_loc.setCurrentText(str(plot.get('legend_loc', 'best')))
        self.plot_ref_lines.setChecked(bool(plot.get('reference_lines', False)))
        self.plot_shade_phases.setChecked(bool(plot.get('shade_phases', False)))
        self.plot_grid.setChecked(bool(plot.get('grid', True)))
        self._fill_series_table(self.primary_table, plot.get('series', []))
        self._fill_series_table(self.secondary_table, plot.get('secondary_series', []))
        self._updating_ui = False
        self._refresh_layout_matrix()
        self._refresh_preview()

    def _clear_subplot_editor(self):
        self._updating_ui = True
        for w in [self.plot_title, self.plot_ylabel, self.plot_y2label]: w.setText('')
        self.plot_legend_loc.setCurrentText('best')
        self.plot_ref_lines.setChecked(False)
        self.plot_shade_phases.setChecked(False)
        self.plot_grid.setChecked(True)
        self.primary_table.setRowCount(0)
        self.secondary_table.setRowCount(0)
        self._updating_ui = False

    def _fill_series_table(self, table: QTableWidget, data: list[dict]):
        table.blockSignals(True)
        table.setRowCount(0)
        for item in data:
            self._add_series_row(table, item, refresh=False)
        table.blockSignals(False)

    def _add_series_row(self, table: QTableWidget, entry: dict | None = None, refresh=True):
        entry = dict(entry or {})
        row = table.rowCount()
        table.insertRow(row)
        combo_key = QComboBox(); combo_key.setEditable(True); combo_key.addItems(AVAILABLE_KEYS); combo_key.setCurrentText(str(entry.get('key', AVAILABLE_KEYS[0]))); combo_key.currentTextChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 0, combo_key)
        table.setItem(row, 1, QTableWidgetItem(str(entry.get('label', entry.get('key', '')))))
        combo_color = QComboBox(); combo_color.setEditable(True); combo_color.addItems(COLOR_PRESETS); combo_color.setCurrentText(str(entry.get('color', ''))); combo_color.currentTextChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 2, combo_color)
        combo_style = QComboBox(); combo_style.setEditable(True); combo_style.addItems(LINESTYLE_PRESETS); combo_style.setCurrentText(str(entry.get('linestyle', ''))); combo_style.currentTextChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 3, combo_style)
        width = QDoubleSpinBox(); width.setRange(0.1, 10.0); width.setValue(float(entry.get('linewidth', 1.5) or 1.5)); width.valueChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 4, width)
        scale = QDoubleSpinBox(); scale.setRange(-1e9, 1e9); scale.setDecimals(6); scale.setValue(float(entry.get('scale', 1.0) or 1.0)); scale.valueChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 5, scale)
        offset = QDoubleSpinBox(); offset.setRange(-1e12, 1e12); offset.setDecimals(6); offset.setValue(float(entry.get('offset', 0.0) or 0.0)); offset.valueChanged.connect(self._subplot_changed)
        table.setCellWidget(row, 6, offset)
        if refresh: self._subplot_changed()

    def _delete_series_row(self, table: QTableWidget):
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)
            self._subplot_changed()

    def _select_from_dialog(self, table: QTableWidget, axis_name: str):
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Signale für {axis_name} auswählen')
        dialog.resize(420, 500)
        lay = QVBoxLayout(dialog)
        lw = QListWidget(); lw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for key in AVAILABLE_KEYS: QListWidgetItem(key, lw)
        lay.addWidget(lw)
        hb = QHBoxLayout(); ok = QPushButton('Übernehmen'); cancel = QPushButton('Abbrechen'); ok.clicked.connect(dialog.accept); cancel.clicked.connect(dialog.reject); hb.addWidget(ok); hb.addWidget(cancel); lay.addLayout(hb)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        for item in lw.selectedItems(): self._add_series_row(table, {'key': item.text(), 'label': item.text()}, refresh=False)
        self._subplot_changed()

    def _series_from_table(self, table: QTableWidget):
        out = []
        for row in range(table.rowCount()):
            combo_key = table.cellWidget(row, 0); combo_color = table.cellWidget(row, 2); combo_style = table.cellWidget(row, 3)
            width = table.cellWidget(row, 4); scale = table.cellWidget(row, 5); offset = table.cellWidget(row, 6)
            key = combo_key.currentText().strip() if isinstance(combo_key, QComboBox) else ''
            label_item = table.item(row, 1); label = label_item.text().strip() if label_item else key
            if not key: continue
            item = {'key': key, 'label': label or key}
            color = combo_color.currentText().strip() if isinstance(combo_color, QComboBox) else ''
            linestyle = combo_style.currentText().strip() if isinstance(combo_style, QComboBox) else ''
            lw = float(width.value()) if isinstance(width, QDoubleSpinBox) else 1.5
            sc = float(scale.value()) if isinstance(scale, QDoubleSpinBox) else 1.0
            of = float(offset.value()) if isinstance(offset, QDoubleSpinBox) else 0.0
            if color: item['color'] = color
            if linestyle: item['linestyle'] = linestyle
            if abs(lw - 1.5) > 1e-12: item['linewidth'] = lw
            if abs(sc - 1.0) > 1e-12: item['scale'] = sc
            if abs(of) > 1e-12: item['offset'] = of
            out.append(item)
        return out

    def _store_current_subplot(self):
        fig = self._get_current_figure()
        idx = self._current_plot_index
        if self._updating_ui or fig is None or idx < 0 or idx >= len(fig.get('plots', [])):
            return
        plot = fig['plots'][idx]
        plot['title'] = self.plot_title.text().strip() or f'Plot {idx+1}'
        plot['ylabel'] = self.plot_ylabel.text().strip()
        plot['y2label'] = self.plot_y2label.text().strip()
        plot['legend_loc'] = self.plot_legend_loc.currentText().strip() or 'best'
        plot['reference_lines'] = self.plot_ref_lines.isChecked()
        plot['shade_phases'] = self.plot_shade_phases.isChecked()
        plot['grid'] = self.plot_grid.isChecked()
        plot['series'] = self._series_from_table(self.primary_table)
        plot['secondary_series'] = self._series_from_table(self.secondary_table)
        item = self.subplot_list.item(idx)
        if item is not None:
            item.setText(f'{idx+1:02d} – {plot["title"]}')

    def _subplot_changed(self, *_):
        if self._updating_ui:
            return
        self._store_current_subplot()
        self._refresh_layout_matrix()
        self._refresh_preview()

    def _add_figure(self):
        self._store_current_subplot(); self._store_current_figure()
        self._figure_models.append({'name': f'Figure {len(self._figure_models)+1}', 'file_suffix': f'f{len(self._figure_models)+1}', 'figsize_in': [13.0, 8.0], 'dpi': 180, 'title': '', 'rows': 1, 'cols': 1, 'sharex': True, 'show_info_box': True, 'info_box_loc': 'upper right', 'auto_save_timestamped': False, 'timestamp_dir': 'timestamped_plots', 'xtick_step_deg': 180.0, 'label_fontsize': 10.0, 'tick_labelsize': 9.0, 'legend_fontsize': 8.0, 'line_width': 1.5, 'plots': []})
        self._refresh_figure_list(len(self._figure_models)-1)
        self._refresh_preview()

    def _copy_figure(self):
        idx = self.figure_list.currentRow()
        if idx < 0: return
        self._store_current_subplot(); self._store_current_figure()
        clone = deepcopy(self._figure_models[idx]); clone['name'] = f"{clone.get('name','Figure')} Kopie"; clone['file_suffix'] = f"{clone.get('file_suffix','copy')}_copy"
        self._figure_models.insert(idx+1, clone)
        self._refresh_figure_list(idx+1); self._refresh_preview()

    def _del_figure(self):
        idx = self.figure_list.currentRow()
        if idx < 0: return
        del self._figure_models[idx]
        if not self._figure_models:
            self._seed_defaults(); return
        self._refresh_figure_list(max(0, idx-1)); self._refresh_preview()

    def _move_figure(self, direction: int):
        idx = self.figure_list.currentRow(); new_idx = idx + direction
        if idx < 0 or new_idx < 0 or new_idx >= len(self._figure_models): return
        self._figure_models[idx], self._figure_models[new_idx] = self._figure_models[new_idx], self._figure_models[idx]
        self._refresh_figure_list(new_idx); self._refresh_preview()

    def _add_plot(self):
        fig = self._get_current_figure();
        if fig is None: return
        self._store_current_subplot()
        fig.setdefault('plots', []).append({'title': f'Plot {len(fig["plots"])+1}', 'ylabel': '', 'y2label': '', 'legend_loc': 'upper right', 'shade_phases': True, 'reference_lines': True, 'grid': True, 'series': [], 'secondary_series': []})
        self._refresh_subplot_list(len(fig['plots'])-1); self._refresh_layout_matrix(); self._refresh_preview()

    def _copy_plot(self):
        fig = self._get_current_figure(); idx = self.subplot_list.currentRow()
        if fig is None or idx < 0 or idx >= len(fig.get('plots', [])): return
        clone = deepcopy(fig['plots'][idx]); clone['title'] = f"{clone.get('title','Plot')} Kopie"; fig['plots'].insert(idx+1, clone)
        self._refresh_subplot_list(idx+1); self._refresh_layout_matrix(); self._refresh_preview()

    def _del_plot(self):
        fig = self._get_current_figure(); idx = self.subplot_list.currentRow()
        if fig is None or idx < 0 or idx >= len(fig.get('plots', [])): return
        del fig['plots'][idx]
        self._refresh_subplot_list(max(0, idx-1)); self._refresh_layout_matrix(); self._refresh_preview()

    def _move_plot(self, direction: int):
        fig = self._get_current_figure(); idx = self.subplot_list.currentRow(); new_idx = idx + direction
        if fig is None or idx < 0 or new_idx < 0 or new_idx >= len(fig.get('plots', [])): return
        fig['plots'][idx], fig['plots'][new_idx] = fig['plots'][new_idx], fig['plots'][idx]
        self._refresh_subplot_list(new_idx); self._refresh_layout_matrix(); self._refresh_preview()

    def _refresh_layout_matrix(self):
        fig = self._get_current_figure()
        rows = max(1, self.rows.value())
        cols = max(1, self.cols.value())
        self.layout_matrix.setRowCount(rows)
        self.layout_matrix.setColumnCount(cols)
        self.layout_matrix.clear()
        if fig is None:
            return
        plots = fig.get('plots', [])
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                text = 'leer'
                if idx < len(plots):
                    text = f'{idx+1:02d}\n{plots[idx].get("title", f"Plot {idx+1}")}'
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout_matrix.setItem(r, c, item)
        self.layout_matrix.resizeColumnsToContents()
        self.layout_matrix.resizeRowsToContents()

    def _matrix_swap_to(self, row: int, col: int):
        fig = self._get_current_figure(); idx = self.subplot_list.currentRow()
        if fig is None or idx < 0: return
        target = row * self.cols.value() + col
        plots = fig.get('plots', [])
        if target >= len(plots) or target == idx: return
        plots[idx], plots[target] = plots[target], plots[idx]
        self._refresh_subplot_list(target)
        self._refresh_layout_matrix()
        self._refresh_preview()

    def build_config(self):
        self._store_current_subplot(); self._store_current_figure()
        figures = []
        for model in self._figure_models:
            fig = {
                'name': model.get('name', ''), 'file_suffix': model.get('file_suffix', ''), 'figsize_in': model.get('figsize_in', [13.0, 10.0]),
                'dpi': model.get('dpi', 180), 'title': model.get('title', ''), 'label_fontsize': model.get('label_fontsize', 10.0),
                'tick_labelsize': model.get('tick_labelsize', 9.0), 'legend_fontsize': model.get('legend_fontsize', 8.0),
                'line_width': model.get('line_width', 1.5), 'rows': model.get('rows', 1), 'cols': model.get('cols', 1),
                'sharex': model.get('sharex', True), 'xtick_step_deg': model.get('xtick_step_deg', 180.0),
                'show_info_box': model.get('show_info_box', True), 'info_box_loc': model.get('info_box_loc', 'upper right'),
                'auto_save_timestamped': model.get('auto_save_timestamped', False), 'timestamp_dir': model.get('timestamp_dir', 'timestamped_plots'),
                'plots': [deepcopy(p) for p in model.get('plots', [])],
            }
            figures.append(fig)
        return {
            'figures': figures,
            'timing_plots': {
                'cartesian': {'enabled': self.timing_cart_enabled.isChecked(), 'auto_save_timestamped': self.timing_cart_auto.isChecked(), 'info_box_loc': self.timing_cart_info.currentText(), 'timestamp_dir': self.timing_dir.text().strip() or 'timestamped_plots'},
                'polar': {'enabled': self.timing_polar_enabled.isChecked(), 'auto_save_timestamped': self.timing_polar_auto.isChecked(), 'timestamp_dir': self.timing_dir.text().strip() or 'timestamped_plots'},
            },
        }

    def _refresh_preview(self, *_):
        cfg = self.build_config()
        try:
            if yaml is None: raise RuntimeError
            txt = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        except Exception:
            import json
            txt = json.dumps(cfg, indent=2, ensure_ascii=False)
        self.yaml_preview.setPlainText(txt)
        if getattr(self, 'preview_auto', None) is not None and self.preview_auto.isChecked():
            self._render_live_preview()

    def _save(self):
        cfg = self.build_config()
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, 'Fehler', 'Bitte Zieldatei angeben.')
            return
        try:
            dump_plot_style_yaml(cfg, path)
        except Exception as exc:
            QMessageBox.critical(self, 'Fehler', str(exc))
            return
        self._refresh_preview()
        QMessageBox.information(self, 'Gespeichert', f'Plot-Konfiguration gespeichert:\n{path}')


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    win = PlotStyleEditor()
    win.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
