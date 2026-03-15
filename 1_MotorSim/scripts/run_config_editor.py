from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import argparse
from motor_sim.gui.config_editor import main as gui_main
from motor_sim.paths import build_paths, initialize_workspace

DEFAULT_PROJECT = str((ROOT / "Projekte").resolve())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open the MotorSim config editor for a project directory.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Project directory containing config.json and data/.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = build_paths(project_dir=args.project)
    initialize_workspace(paths, copy_defaults=True, copy_reference_data=False)
    os.environ["MOTORSIM_PROJECT_DIR"] = str(paths.project_dir)
    os.chdir(paths.project_dir)
    return int(gui_main())


if __name__ == "__main__":
    raise SystemExit(main())
