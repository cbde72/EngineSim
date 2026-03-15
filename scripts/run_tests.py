from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time
import webbrowser
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from motor_sim.paths import build_paths, initialize_workspace

DEFAULT_PROJECT = str((ROOT / "Projekte").resolve())
DEFAULT_TEST_SPACE = str((ROOT.parent / "test_space").resolve())


class TestConfig:
    def __init__(
        self,
        project: str,
        test_space: str,
        html: bool = False,
        coverage: bool = False,
        durations: int = 0,
        keyword: str | None = None,
        file: str | None = None,
        failfast: bool = False,
        verbose: bool = True,
        open_html_report: bool = False,
        open_coverage_report: bool = False,
        show_live_status: bool = True,
        status_prefix: str = "MotorSim pytest",
    ):
        self.project = project
        self.test_space = test_space
        self.html = html
        self.coverage = coverage
        self.durations = durations
        self.keyword = keyword
        self.file = file
        self.failfast = failfast
        self.verbose = verbose
        self.open_html_report = open_html_report
        self.open_coverage_report = open_coverage_report
        self.show_live_status = show_live_status
        self.status_prefix = status_prefix


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


def build_pytest_command(cfg: TestConfig, html_report: Path, coverage_dir: Path, pytest_log: Path) -> list[str]:
    cmd = ["pytest"]

    # kompakte Konsolenausgabe wie früher
    cmd.append("-q")
    cmd.append("--disable-warnings")
    if cfg.failfast:
        cmd.append("-x")

    # pytest.log immer in test_space schreiben
    pytest_log.parent.mkdir(parents=True, exist_ok=True)
    cmd.append(f"--log-file={pytest_log}")
    cmd.append("--log-file-level=INFO")

    # HTML-Report immer in test_space/report.html
    html_available = importlib.util.find_spec("pytest_html") is not None
    if html_available:
        html_report.parent.mkdir(parents=True, exist_ok=True)
        cmd.append(f"--html={html_report}")
        cmd.append("--self-contained-html")

    # Coverage immer in test_space/htmlcov
    cmd.extend(["--cov=src", f"--cov-report=html:{coverage_dir}", "--cov-report=term-missing:skip-covered"])

    if cfg.durations and cfg.durations > 0:
        cmd.append(f"--durations={cfg.durations}")
    if cfg.keyword:
        cmd.extend(["-k", cfg.keyword])
    if cfg.file:
        cmd.append(cfg.file)

    return cmd


def _format_elapsed(seconds: float) -> str:
    seconds_i = int(seconds)
    minutes, sec = divmod(seconds_i, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _status_line(prefix: str, spinner_char: str, elapsed_s: float, cmd: list[str]) -> str:
    cmd_short = " ".join(cmd)
    if len(cmd_short) > 95:
        cmd_short = cmd_short[:92] + "..."
    return f"\r{prefix} {spinner_char} | elapsed {_format_elapsed(elapsed_s)} | {cmd_short}"


def _clear_status_line(last_len: int) -> None:
    sys.stdout.write("\r" + " " * last_len + "\r")
    sys.stdout.flush()


def run_pytest(cfg: TestConfig) -> int:
    paths = build_paths(project_dir=cfg.project, test_space_dir=cfg.test_space)
    
    initialize_workspace(paths, copy_defaults=True, copy_reference_data=False)
    
    html_report = paths.html_report_path
    
    coverage_dir = paths.coverage_dir
    
    pytest_log = paths.test_space_dir / "pytest.log"
    pytest_log.parent.mkdir(parents=True, exist_ok=True)
    
    if coverage_dir.exists():
        shutil.rmtree(coverage_dir, ignore_errors=True)
        
    #cmd = build_pytest_command(cfg, html_report, coverage_dir)
    cmd = build_pytest_command(cfg, html_report, coverage_dir, pytest_log)
    print("\nRunning pytest in:")
    print(paths.code_root)
    print("\nProject input:")
    print(paths.project_dir)
    print("\nTest space:")
    print(paths.test_space_dir)
    print("\nCommand:")
    print(" ".join(cmd))
    print()

    env = os.environ.copy()
    env["MOTORSIM_PROJECT_DIR"] = str(paths.project_dir)
    env["MOTORSIM_TEST_SPACE"] = str(paths.test_space_dir)

    process = subprocess.Popen(cmd, cwd=paths.code_root, env=env)
    start_time = time.perf_counter()
    spinner = ["|", "/", "-", "\\"]
    spin_idx = 0
    last_line_len = 0

    while process.poll() is None:
        if cfg.show_live_status:
            elapsed = time.perf_counter() - start_time
            line = _status_line(cfg.status_prefix, spinner[spin_idx % len(spinner)], elapsed, cmd)
            sys.stdout.write(line)
            sys.stdout.flush()
            last_line_len = max(last_line_len, len(line))
            spin_idx += 1
        time.sleep(0.2)

    rc = process.returncode
    elapsed_total = time.perf_counter() - start_time
    if cfg.show_live_status:
        _clear_status_line(last_line_len)
    print(f"Finished after {_format_elapsed(elapsed_total)}")

    if cfg.html and html_report.exists():
        print("\nHTML report:")
        print(html_report.resolve())
        if cfg.open_html_report:
            webbrowser.open(html_report.resolve().as_uri())

    cov_report = coverage_dir / "index.html"
    if cfg.coverage and cov_report.exists():
        print("\nCoverage report:")
        print(cov_report.resolve())
        if cfg.open_coverage_report:
            webbrowser.open(cov_report.resolve().as_uri())

    return int(rc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pytest with MotorSim project/test_space paths.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Project directory containing config.json and data/.")
    parser.add_argument("--test-space", default=DEFAULT_TEST_SPACE, help="Target test_space directory.")
    parser.add_argument("--pick-project", action="store_true")
    parser.add_argument("--pick-test-space", action="store_true")
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--durations", type=int, default=0)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--file", default=None)
    parser.add_argument("--failfast", action="store_true")
    parser.add_argument("--quiet", action="store_true")
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
    cfg = TestConfig(
        project=str(project),
        test_space=str(test_space),
        html=args.html,
        coverage=args.coverage,
        durations=args.durations,
        keyword=args.keyword,
        file=args.file,
        failfast=args.failfast,
        verbose=not args.quiet,
    )
    return run_pytest(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
