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

from motor_sim.paths import build_paths, initialize_workspace
from tools.generate_cycle_reference import generate_reference

DEFAULT_PROJECT = str((ROOT / "Projekte").resolve())
DEFAULT_TEST_SPACE = str((ROOT.parent / "test_space").resolve())


def ask_directory(title: str) -> Path | None:
    try:
        from tkinter import Tk, filedialog
    except Exception:
        return None
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return Path(folder).resolve() if folder else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MotorSim cycle reference data.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Project directory containing config.json and data/.")
    parser.add_argument("--test-space", default=DEFAULT_TEST_SPACE, help="Target test_space directory.")
    parser.add_argument("--pick-project", action="store_true")
    parser.add_argument("--pick-test-space", action="store_true")
    parser.add_argument("--config-name", default="config.json", help="Config filename inside the project directory.")
    parser.add_argument("--output-name", default="cycle_reference_default.npz", help="Reference filename inside test_space/reference_data/.")
    return parser.parse_args()


def _resolve_dir(cli_value: str | None, default_value: str, title: str, pick: bool) -> Path:
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    if default_value.strip():
        return Path(default_value).expanduser().resolve()
    if pick:
        p = ask_directory(title)
        if p is not None:
            return p
    raise RuntimeError(f"{title} nicht angegeben. Nutze CLI-Argument oder DEFAULT_* im Script.")


def main() -> int:
    args = parse_args()
    project = _resolve_dir(args.project, DEFAULT_PROJECT, "MotorSim Projektordner auswählen", args.pick_project)
    test_space = _resolve_dir(args.test_space, DEFAULT_TEST_SPACE, "MotorSim test_space auswählen", args.pick_test_space)
    paths = build_paths(project_dir=project, test_space_dir=test_space)
    initialize_workspace(paths, copy_defaults=True, copy_reference_data=False)
    out = generate_reference(paths.project_dir, paths.test_space_dir, args.config_name, args.output_name)
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
