from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from motor_sim.gui.config_defaults import get_default_config, normalize_config
from motor_sim.gui.config_editor import ConfigFieldFactory, DARK_STYLESHEET, LIGHT_STYLESHEET
from motor_sim.paths import build_paths, initialize_workspace

DEFAULT_PROJECT = str((ROOT / "Projekte").resolve())
SPECIES_OPTIONS = [
    "air", "dry_air", "luft",
    "methanol", "CH3OH",
    "ethanol", "C2H5OH",
    "benzin", "isooctane", "IC8H18",
    "diesel", "n-dodecane", "NC12H26",
    "wasserstoff", "hydrogen", "H2",
    "O2", "N2", "AR", "CO2", "H2O", "CO", "NO", "NO2", "OH", "O", "H", "HO2", "H2O2",
]
FUEL_OPTIONS = ["methanol", "ethanol", "benzin", "diesel", "wasserstoff"]
THERMO_MODE_OPTIONS = ["const", "nasa7_species", "nasa7_mixture"]
MIXTURE_PRESET_OPTIONS = ["custom", "air", "combustion_products"]
LAMBDA_SOURCE_OPTIONS = ["config", "combustion", "gas"]
RICH_MODE_OPTIONS = ["simple", "extended"]
EQ_TEMP_SOURCE_OPTIONS = ["config", "cylinder"]


class ThermoGasEditor(QWidget):
    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = Path(config_path)
        self._cfg: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        info = QGroupBox("Zweck")
        info_lay = QVBoxLayout(info)
        info_lay.addWidget(QLabel(
            "Dieser Editor schreibt nur die heute hinzugefügten Gas-/Thermo-/Equilibrium-Felder in config.json.\n"
            "Alle anderen Konfigurationsbereiche bleiben unverändert.\n\n"
            "Unterstützt:\n"
            "- gas.thermo_mode\n"
            "- NASA7 species / mixture / combustion_products\n"
            "- rich_products simple/extended\n"
            "- equilibrium-lite inkl. temperature_source und clamp"
        ))
        left_lay.addWidget(info)

        box_mode = QGroupBox("Thermo mode")
        fm = QFormLayout(box_mode)
        self.thermo_mode = ConfigFieldFactory.combo(THERMO_MODE_OPTIONS, "const")
        self.R = ConfigFieldFactory.dspin(287.0, 1.0, 1e6, 1.0, 6)
        self.cp = ConfigFieldFactory.dspin(1005.0, 1.0, 1e7, 1.0, 6)
        fm.addRow("thermo_mode", self.thermo_mode)
        fm.addRow("R_J_per_kgK", self.R)
        fm.addRow("cp_J_per_kgK", self.cp)
        left_lay.addWidget(box_mode)

        box_species = QGroupBox("NASA7 single species")
        fs = QFormLayout(box_species)
        self.species_name = ConfigFieldFactory.combo(SPECIES_OPTIONS, "air")
        fs.addRow("species_name", self.species_name)
        left_lay.addWidget(box_species)

        box_mix = QGroupBox("NASA7 mixture")
        fmix = QFormLayout(box_mix)
        self.mixture_preset = ConfigFieldFactory.combo(MIXTURE_PRESET_OPTIONS, "custom")
        self.custom_mix = QPlainTextEdit()
        self.custom_mix.setPlaceholderText('{\n  "N2": 0.78084,\n  "O2": 0.20946,\n  "AR": 0.00934\n}')
        self.custom_mix.setMinimumHeight(170)
        fmix.addRow("mixture_preset", self.mixture_preset)
        fmix.addRow("mixture_mole_fractions", self.custom_mix)
        left_lay.addWidget(box_mix)

        left_lay.addStretch(1)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(10)

        box_prod = QGroupBox("Combustion products")
        fp = QFormLayout(box_prod)
        self.fuel_name = ConfigFieldFactory.combo(FUEL_OPTIONS, "methanol")
        self.lambda_value = ConfigFieldFactory.dspin(1.0, 0.0, 10.0, 0.01, 6)
        self.lambda_source = ConfigFieldFactory.combo(LAMBDA_SOURCE_OPTIONS, "combustion")
        self.rich_mode = ConfigFieldFactory.combo(RICH_MODE_OPTIONS, "simple")
        fp.addRow("combustion_products_fuel_name", self.fuel_name)
        fp.addRow("combustion_products_lambda", self.lambda_value)
        fp.addRow("combustion_products_lambda_source", self.lambda_source)
        fp.addRow("combustion_products_rich_mode", self.rich_mode)
        right_lay.addWidget(box_prod)

        box_eq = QGroupBox("Equilibrium-lite")
        fe = QFormLayout(box_eq)
        self.eq_enabled = ConfigFieldFactory.check(False)
        self.eq_temp_K = ConfigFieldFactory.dspin(2200.0, 0.0, 10000.0, 10.0, 3)
        self.eq_strength = ConfigFieldFactory.dspin(0.35, 0.0, 1.0, 0.01, 4)
        self.eq_temp_source = ConfigFieldFactory.combo(EQ_TEMP_SOURCE_OPTIONS, "config")
        self.eq_temp_min = ConfigFieldFactory.dspin(1200.0, 0.0, 10000.0, 10.0, 3)
        self.eq_temp_max = ConfigFieldFactory.dspin(3000.0, 0.0, 10000.0, 10.0, 3)
        fe.addRow("enabled", self.eq_enabled)
        fe.addRow("temperature_K", self.eq_temp_K)
        fe.addRow("strength", self.eq_strength)
        fe.addRow("temperature_source", self.eq_temp_source)
        fe.addRow("temperature_min_K", self.eq_temp_min)
        fe.addRow("temperature_max_K", self.eq_temp_max)
        right_lay.addWidget(box_eq)

        box_preview = QGroupBox("Preview / effective gas block")
        pv = QVBoxLayout(box_preview)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(300)
        pv.addWidget(self.preview)
        right_lay.addWidget(box_preview, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([620, 700])
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.btn_reload = QPushButton("Reload")
        self.btn_defaults = QPushButton("Nur Gas-Defaults laden")
        self.btn_backup = QPushButton("Backup anlegen")
        self.btn_save = QPushButton("Save")
        buttons.addWidget(self.btn_reload)
        buttons.addWidget(self.btn_defaults)
        buttons.addWidget(self.btn_backup)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

        for w in [
            self.thermo_mode, self.species_name, self.mixture_preset, self.fuel_name,
            self.lambda_source, self.rich_mode, self.eq_temp_source,
        ]:
            w.currentTextChanged.connect(self._sync_ui)
            w.currentTextChanged.connect(self._update_preview)
        for w in [
            self.R, self.cp, self.lambda_value, self.eq_temp_K, self.eq_strength,
            self.eq_temp_min, self.eq_temp_max,
        ]:
            w.valueChanged.connect(self._update_preview)
        self.eq_enabled.stateChanged.connect(self._sync_ui)
        self.eq_enabled.stateChanged.connect(self._update_preview)
        self.custom_mix.textChanged.connect(self._update_preview)

        self.btn_reload.clicked.connect(self.load_from_disk)
        self.btn_defaults.clicked.connect(self.load_gas_defaults)
        self.btn_backup.clicked.connect(self.create_backup)
        self.btn_save.clicked.connect(self.save_to_disk)

        self.load_from_disk()

    def _normalize_mixture_text(self, value: dict | None) -> str:
        value = dict(value or {})
        if not value:
            value = {"N2": 0.78084, "O2": 0.20946, "AR": 0.00934}
        return json.dumps(value, indent=2, ensure_ascii=False)

    def _parse_custom_mixture(self) -> dict:
        raw = self.custom_mix.toPlainText().strip()
        if not raw:
            return {"N2": 0.78084, "O2": 0.20946, "AR": 0.00934}
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("mixture_mole_fractions muss ein JSON-Objekt sein")
        out = {}
        for key, value in data.items():
            name = str(key).strip()
            if not name:
                continue
            out[name] = float(value)
        if not out:
            raise ValueError("mixture_mole_fractions darf nicht leer sein")
        return out

    def _gas_block_from_widgets(self) -> dict:
        gas = {
            "R_J_per_kgK": float(self.R.value()),
            "cp_J_per_kgK": float(self.cp.value()),
            "thermo_mode": self.thermo_mode.currentText(),
            "species_name": self.species_name.currentText(),
            "mixture_preset": self.mixture_preset.currentText(),
            "mixture_mole_fractions": self._parse_custom_mixture(),
            "combustion_products_fuel_name": self.fuel_name.currentText(),
            "combustion_products_lambda": float(self.lambda_value.value()),
            "combustion_products_lambda_source": self.lambda_source.currentText(),
            "combustion_products_rich_mode": self.rich_mode.currentText(),
            "combustion_products_equilibrium_lite_enabled": bool(self.eq_enabled.isChecked()),
            "combustion_products_equilibrium_lite_temperature_K": float(self.eq_temp_K.value()),
            "combustion_products_equilibrium_lite_strength": float(self.eq_strength.value()),
            "combustion_products_equilibrium_lite_temperature_source": self.eq_temp_source.currentText(),
            "combustion_products_equilibrium_lite_temperature_min_K": float(self.eq_temp_min.value()),
            "combustion_products_equilibrium_lite_temperature_max_K": float(self.eq_temp_max.value()),
        }
        return gas

    def _sync_ui(self):
        mode = self.thermo_mode.currentText().strip().lower()
        preset = self.mixture_preset.currentText().strip().lower()
        eq_enabled = bool(self.eq_enabled.isChecked())
        eq_source = self.eq_temp_source.currentText().strip().lower()

        const_mode = mode == "const"
        species_mode = mode == "nasa7_species"
        mixture_mode = mode == "nasa7_mixture"
        custom_mode = mixture_mode and preset == "custom"
        products_mode = mixture_mode and preset == "combustion_products"
        cylinder_temp_mode = products_mode and eq_enabled and eq_source == "cylinder"

        self.species_name.setEnabled(species_mode)
        self.mixture_preset.setEnabled(mixture_mode)
        self.custom_mix.setEnabled(custom_mode)

        self.fuel_name.setEnabled(products_mode)
        self.lambda_value.setEnabled(products_mode)
        self.lambda_source.setEnabled(products_mode)
        self.rich_mode.setEnabled(products_mode)
        self.eq_enabled.setEnabled(products_mode)
        self.eq_temp_K.setEnabled(products_mode and eq_enabled and not cylinder_temp_mode)
        self.eq_strength.setEnabled(products_mode and eq_enabled)
        self.eq_temp_source.setEnabled(products_mode and eq_enabled)
        self.eq_temp_min.setEnabled(products_mode and eq_enabled and eq_source == "cylinder")
        self.eq_temp_max.setEnabled(products_mode and eq_enabled and eq_source == "cylinder")

        self.R.setEnabled(True)
        self.cp.setEnabled(True)
        # R/cp bleiben editierbar, auch wenn NASA7 aktiv ist, damit der Block vollständig konsistent bleibt.
        _ = const_mode

    def _update_preview(self):
        try:
            gas = self._gas_block_from_widgets()
            text = json.dumps(gas, indent=2, ensure_ascii=False)
            self.preview.setPlainText(text)
        except Exception as exc:
            self.preview.setPlainText(f"Ungültige Eingabe:\n{exc}")

    def load_from_disk(self):
        if not self.config_path.exists():
            QMessageBox.warning(self, "Config fehlt", f"Datei nicht gefunden:\n{self.config_path}")
            return
        with self.config_path.open("r", encoding="utf-8") as f:
            raw_cfg = json.load(f)
        self._cfg = normalize_config(raw_cfg)
        gas = dict(self._cfg.get("gas", {}))

        self.R.setValue(float(gas.get("R_J_per_kgK", 287.0)))
        self.cp.setValue(float(gas.get("cp_J_per_kgK", 1005.0)))
        self.thermo_mode.setCurrentText(str(gas.get("thermo_mode", "const")))
        self.species_name.setCurrentText(str(gas.get("species_name", "air")))
        self.mixture_preset.setCurrentText(str(gas.get("mixture_preset", "custom")))
        self.custom_mix.setPlainText(self._normalize_mixture_text(gas.get("mixture_mole_fractions", {})))
        self.fuel_name.setCurrentText(str(gas.get("combustion_products_fuel_name", gas.get("species_name", "methanol"))))
        src = str(gas.get("combustion_products_lambda_source", "combustion"))
        if src == "fixed":
            src = "config"
        self.lambda_source.setCurrentText(src if src in LAMBDA_SOURCE_OPTIONS else "combustion")
        self.lambda_value.setValue(float(gas.get("combustion_products_lambda", 1.0)))
        self.rich_mode.setCurrentText(str(gas.get("combustion_products_rich_mode", "simple")))
        self.eq_enabled.setChecked(bool(gas.get("combustion_products_equilibrium_lite_enabled", False)))
        self.eq_temp_K.setValue(float(gas.get("combustion_products_equilibrium_lite_temperature_K", 2200.0)))
        self.eq_strength.setValue(float(gas.get("combustion_products_equilibrium_lite_strength", 0.35)))
        self.eq_temp_source.setCurrentText(str(gas.get("combustion_products_equilibrium_lite_temperature_source", "config")))
        self.eq_temp_min.setValue(float(gas.get("combustion_products_equilibrium_lite_temperature_min_K", 1200.0)))
        self.eq_temp_max.setValue(float(gas.get("combustion_products_equilibrium_lite_temperature_max_K", 3000.0)))
        self._sync_ui()
        self._update_preview()

    def load_gas_defaults(self):
        cfg = get_default_config()
        gas = dict(cfg.get("gas", {}))
        gas.setdefault("thermo_mode", "const")
        gas.setdefault("species_name", "air")
        gas.setdefault("mixture_preset", "custom")
        gas.setdefault("mixture_mole_fractions", {"N2": 0.78084, "O2": 0.20946, "AR": 0.00934})
        gas.setdefault("combustion_products_fuel_name", "methanol")
        gas.setdefault("combustion_products_lambda", 1.0)
        gas.setdefault("combustion_products_lambda_source", "combustion")
        gas.setdefault("combustion_products_rich_mode", "simple")
        gas.setdefault("combustion_products_equilibrium_lite_enabled", False)
        gas.setdefault("combustion_products_equilibrium_lite_temperature_K", 2200.0)
        gas.setdefault("combustion_products_equilibrium_lite_strength", 0.35)
        gas.setdefault("combustion_products_equilibrium_lite_temperature_source", "config")
        gas.setdefault("combustion_products_equilibrium_lite_temperature_min_K", 1200.0)
        gas.setdefault("combustion_products_equilibrium_lite_temperature_max_K", 3000.0)

        self.R.setValue(float(gas["R_J_per_kgK"]))
        self.cp.setValue(float(gas["cp_J_per_kgK"]))
        self.thermo_mode.setCurrentText(str(gas["thermo_mode"]))
        self.species_name.setCurrentText(str(gas["species_name"]))
        self.mixture_preset.setCurrentText(str(gas["mixture_preset"]))
        self.custom_mix.setPlainText(self._normalize_mixture_text(gas["mixture_mole_fractions"]))
        self.fuel_name.setCurrentText(str(gas["combustion_products_fuel_name"]))
        self.lambda_value.setValue(float(gas["combustion_products_lambda"]))
        self.lambda_source.setCurrentText(str(gas["combustion_products_lambda_source"]))
        self.rich_mode.setCurrentText(str(gas["combustion_products_rich_mode"]))
        self.eq_enabled.setChecked(bool(gas["combustion_products_equilibrium_lite_enabled"]))
        self.eq_temp_K.setValue(float(gas["combustion_products_equilibrium_lite_temperature_K"]))
        self.eq_strength.setValue(float(gas["combustion_products_equilibrium_lite_strength"]))
        self.eq_temp_source.setCurrentText(str(gas["combustion_products_equilibrium_lite_temperature_source"]))
        self.eq_temp_min.setValue(float(gas["combustion_products_equilibrium_lite_temperature_min_K"]))
        self.eq_temp_max.setValue(float(gas["combustion_products_equilibrium_lite_temperature_max_K"]))
        self._sync_ui()
        self._update_preview()

    def create_backup(self):
        target = self.config_path.with_suffix(self.config_path.suffix + ".bak")
        i = 1
        while target.exists():
            target = self.config_path.with_name(f"{self.config_path.stem}.bak{i}{self.config_path.suffix}")
            i += 1
        shutil.copy2(self.config_path, target)
        window = self.window()
        if isinstance(window, QMainWindow) and window.statusBar() is not None:
            window.statusBar().showMessage(f"Backup erstellt: {target}", 5000)
        else:
            QMessageBox.information(self, "Backup", f"Backup erstellt:\n{target}")

    def save_to_disk(self):
        try:
            gas = self._gas_block_from_widgets()
        except Exception as exc:
            QMessageBox.critical(self, "Ungültige Eingabe", str(exc))
            return

        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        cfg["gas"] = gas

        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")

        self._cfg = cfg
        window = self.window()
        if isinstance(window, QMainWindow) and window.statusBar() is not None:
            window.statusBar().showMessage(f"Gespeichert: {self.config_path}", 5000)
        QMessageBox.information(self, "Gespeichert", f"Gas-/Thermo-Block gespeichert:\n{self.config_path}")


class ThermoGasEditorWindow(QMainWindow):
    def __init__(self, config_path: Path):
        super().__init__()
        self.setWindowTitle("MotorSim Thermo/Gas Config Editor")
        self.resize(1380, 900)
        self.editor = ThermoGasEditor(config_path=config_path, parent=self)
        self.setCentralWidget(self.editor)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(str(config_path))


def _pick_project_dir(default_dir: str) -> str:
    app = QApplication.instance() or QApplication(sys.argv)
    project_dir = QFileDialog.getExistingDirectory(None, "MotorSim-Projekt auswählen", default_dir)
    return project_dir or default_dir


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Open a focused MotorSim thermo/gas config editor.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Project directory containing config.json")
    parser.add_argument("--pick-project", action="store_true", help="Open a directory picker before startup")
    parser.add_argument("--dark", action="store_true", help="Start with dark theme")
    args = parser.parse_args()

    project_dir = args.project
    if args.pick_project:
        project_dir = _pick_project_dir(project_dir)

    paths = build_paths(project_dir=project_dir)
    initialize_workspace(paths, copy_defaults=True, copy_reference_data=False)
    os.environ["MOTORSIM_PROJECT_DIR"] = str(paths.project_dir)
    os.chdir(paths.project_dir)
    config_path = Path(paths.project_dir) / "config.json"

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET if args.dark else LIGHT_STYLESHEET)
    win = ThermoGasEditorWindow(config_path=config_path)
    win.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
