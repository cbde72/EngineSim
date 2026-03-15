from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QWidget

from motor_sim.paths import build_paths, initialize_workspace, ProjectPaths


def default_plot_candidates(paths: ProjectPaths) -> list[Path]:
    return [
        paths.workspace_root / 'plot.yaml',
        paths.workspace_root / 'plot.yml',
        paths.workspace_root / 'plot.json',
        paths.project_root / 'plot.yaml',
        paths.project_root / 'plot.yml',
        paths.project_root / 'plot.json',
    ]


def default_preview_candidates(paths: ProjectPaths) -> list[Path]:
    return [
        paths.workspace_root / 'out' / 'out_gui.csv',
        paths.workspace_root / 'results' / 'out_gui.csv',
        paths.workspace_root / 'out_gui.csv',
        paths.project_root / 'out' / 'out_gui.csv',
        paths.project_root / 'results' / 'out_gui.csv',
    ]


def first_existing(candidates: list[Path]) -> Optional[Path]:
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def choose_workspace(parent: QWidget | None, start_dir: str | Path | None = None, title: str = 'MotorSim Arbeitsverzeichnis auswählen') -> Path | None:
    start = str(Path(start_dir).expanduser().resolve()) if start_dir else str(Path.cwd())
    folder = QFileDialog.getExistingDirectory(parent, title, start)
    if not folder:
        return None
    return Path(folder).expanduser().resolve()


def activate_workspace(workspace: str | Path | None, init_if_missing: bool = False) -> ProjectPaths:
    paths = build_paths(workspace)
    if init_if_missing:
        initialize_workspace(paths)
    return paths
