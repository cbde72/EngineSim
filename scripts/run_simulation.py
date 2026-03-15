from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from motor_sim.main import run_case
from motor_sim.paths import build_paths, initialize_workspace

DEFAULT_PROJECT = str((ROOT / "Projekte").resolve())
DEFAULT_TEST_SPACE = str((ROOT.parent / "test_space").resolve())


def ask_project_dir() -> Path | None:
    try:
        from tkinter import Tk, filedialog
    except Exception:
        return None

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="MotorSim Projektordner auswählen")
    root.destroy()

    if not folder:
        return None
    return Path(folder).resolve()


def parse_args():
    parser = argparse.ArgumentParser(description="MotorSim Simulation starten")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT, help="Projektordner mit config.json, data/, optional plot.yaml")
    parser.add_argument("--test-space", type=str, default=DEFAULT_TEST_SPACE, help="Test-Space für Referenzdaten / Reports")
    parser.add_argument("--pick-project", action="store_true", help="Projektordner per Dialog auswählen")
    parser.add_argument("--no-gui-pick", action="store_true", help="Keinen Dialog öffnen, wenn kein Projekt gefunden wurde")
    return parser.parse_args()


def _configured_default_project() -> Path | None:
    if not DEFAULT_PROJECT.strip():
        return None
    p = Path(DEFAULT_PROJECT).expanduser().resolve()
    return p if p.exists() else None


def _configured_default_test_space() -> Path | None:
    if not DEFAULT_TEST_SPACE.strip():
        return None
    p = Path(DEFAULT_TEST_SPACE).expanduser().resolve()
    return p if p.exists() else p


def resolve_project_dir(args) -> Path:
    if args.project:
        return Path(args.project).expanduser().resolve()

    p = _configured_default_project()
    if p is not None:
        print(f"[INFO] Verwende DEFAULT_PROJECT: {p}")
        return p

    if args.pick_project:
        p = ask_project_dir()
        if p is not None:
            return p

    if not args.no_gui_pick:
        print("[INFO] Kein Projekt per CLI angegeben - öffne Projektauswahl...")
        p = ask_project_dir()
        if p is not None:
            return p

    raise RuntimeError("Kein Projektordner gefunden. Nutze --project <Pfad> oder setze DEFAULT_PROJECT im Script.")


def run():
    args = parse_args()
    project_dir = resolve_project_dir(args)
    test_space_dir = args.test_space or _configured_default_test_space()

    paths = build_paths(project_dir=project_dir, test_space_dir=test_space_dir)
    initialize_workspace(paths, copy_defaults=True, copy_reference_data=False)

    print(f"[INFO] Projektordner: {paths.project_dir}")
    print(f"[INFO] Config:        {paths.project_config_file}")
    print(f"[INFO] Data:          {paths.project_data_dir}")
    print(f"[INFO] Output:        {paths.project_out_dir}")

    raise SystemExit(run_case(str(paths.project_config_file)))


if __name__ == "__main__":
    run()
