from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ENV_PROJECT_DIR = "MOTORSIM_PROJECT_DIR"
ENV_TEST_SPACE_DIR = "MOTORSIM_TEST_SPACE"
ENV_WORKDIR = "MOTORSIM_WORKDIR"  # backward compatibility


def find_code_root(start: str | Path | None = None) -> Path:
    p = Path(start or __file__).resolve()
    search = [p if p.is_dir() else p.parent, *(p.parents if not p.is_dir() else p.parents)]
    for cand in search:
        if (cand / "src").exists() and (cand / "tests").exists():
            return cand.resolve()
    return Path(__file__).resolve().parents[2]


def _resolve_optional_dir(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return Path(s).expanduser().resolve()


def resolve_project_dir(project_dir: str | Path | None = None) -> Path:
    explicit = _resolve_optional_dir(project_dir)
    if explicit is not None:
        return explicit
    for env_name in (ENV_PROJECT_DIR, ENV_WORKDIR):
        env = _resolve_optional_dir(os.getenv(env_name))
        if env is not None:
            return env
    code_root = find_code_root()
    default_project = code_root / 'Projekte'
    if default_project.exists():
        return default_project.resolve()
    return Path.cwd().resolve()


def resolve_test_space_dir(test_space_dir: str | Path | None = None) -> Path:
    explicit = _resolve_optional_dir(test_space_dir)
    if explicit is not None:
        return explicit
    env = _resolve_optional_dir(os.getenv(ENV_TEST_SPACE_DIR))
    if env is not None:
        return env
    return (find_code_root().parent / "test_space").resolve()


@dataclass(frozen=True)
class MotorSimPaths:
    code_root: Path
    project_dir: Path
    test_space_dir: Path

    # canonical API
    @property
    def project_config_file(self) -> Path:
        return self.project_dir / "config.json"

    @property
    def project_data_dir(self) -> Path:
        return self.project_dir / "data"

    @property
    def project_out_dir(self) -> Path:
        return self.project_dir / "out"

    @property
    def project_plot_yaml(self) -> Path:
        return self.project_dir / "plot.yaml"

    @property
    def reference_data_dir(self) -> Path:
        return self.test_space_dir / "reference_data"

    @property
    def html_report_path(self) -> Path:
        return self.test_space_dir / "report.html"

    @property
    def coverage_dir(self) -> Path:
        return self.test_space_dir / "htmlcov"

    # backward-compatible aliases used by older patches / GUI helpers
    @property
    def workspace_root(self) -> Path:
        return self.project_dir

    @property
    def project_root(self) -> Path:
        return self.code_root

    @property
    def workspace_config_file(self) -> Path:
        return self.project_config_file

    @property
    def workspace_data_dir(self) -> Path:
        return self.project_data_dir

    @property
    def results_dir(self) -> Path:
        return self.project_out_dir

    @property
    def plots_dir(self) -> Path:
        return self.project_out_dir / 'plots'

    @property
    def logs_dir(self) -> Path:
        return self.project_out_dir / 'logs'

    @property
    def exports_dir(self) -> Path:
        return self.project_out_dir / 'exports'

    def ensure_runtime_dirs(self) -> None:
        for d in (
            self.project_dir,
            self.project_data_dir,
            self.project_out_dir,
            self.test_space_dir,
            self.reference_data_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def ensure_output_subdirs(self) -> None:
        for d in (self.project_out_dir, self.plots_dir, self.logs_dir, self.exports_dir):
            d.mkdir(parents=True, exist_ok=True)


ProjectPaths = MotorSimPaths


def build_paths(
    project_dir: str | Path | None = None,
    test_space_dir: str | Path | None = None,
) -> MotorSimPaths:
    paths = MotorSimPaths(
        code_root=find_code_root(project_dir),
        project_dir=resolve_project_dir(project_dir),
        test_space_dir=resolve_test_space_dir(test_space_dir),
    )
    paths.ensure_runtime_dirs()
    return paths


def _copy_tree_missing(src_root: Path, dst_root: Path) -> list[Path]:
    created: list[Path] = []
    if not src_root.exists():
        return created
    for src in src_root.rglob('*'):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            created.append(dst)
    return created


def initialize_workspace(
    project_dir: str | Path | MotorSimPaths | None = None,
    test_space_dir: str | Path | None = None,
    *,
    copy_defaults: bool = True,
    copy_reference_data: bool = False,
) -> list[Path]:
    """
    Initialize project and test-space directories and return a list of newly created files.

    Accepts either a MotorSimPaths object or explicit project/test-space directories so older
    call sites like initialize_workspace(build_paths(...)) keep working.
    """
    if isinstance(project_dir, MotorSimPaths):
        paths = project_dir
    else:
        paths = build_paths(project_dir=project_dir, test_space_dir=test_space_dir)

    paths.ensure_runtime_dirs()
    paths.ensure_output_subdirs()

    created: list[Path] = []
    if not copy_defaults:
        return created

    code_root = paths.code_root
    default_config = code_root / 'config.json'
    default_data = code_root / 'data'
    default_plot_yaml = code_root / 'plot.yaml'
    default_reference_data = code_root / 'tests' / 'reference_data'

    if default_config.exists() and not paths.project_config_file.exists():
        paths.project_config_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(default_config, paths.project_config_file)
        created.append(paths.project_config_file)

    if default_plot_yaml.exists() and not paths.project_plot_yaml.exists():
        shutil.copy2(default_plot_yaml, paths.project_plot_yaml)
        created.append(paths.project_plot_yaml)

    created.extend(_copy_tree_missing(default_data, paths.project_data_dir))

    if copy_reference_data:
        created.extend(_copy_tree_missing(default_reference_data, paths.reference_data_dir))

    return created


def resolve_input_file(config_path: str | Path, value: str | Path) -> Path:
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()

    config_dir = Path(config_path).resolve().parent
    candidates = [
        (config_dir / p).resolve(),
        (config_dir / 'data' / p).resolve(),
    ]
    code_root = find_code_root(config_path)
    candidates.extend([
        (code_root / p).resolve(),
        (code_root / 'data' / p).resolve(),
        (code_root / 'Projekte' / p).resolve(),
        (code_root / 'Projekte' / 'data' / p).resolve(),
    ])
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[1]


def resolve_output_dir(config_path: str | Path, out_dir: str | Path | None) -> Path:
    p = Path(out_dir or 'out').expanduser()
    if p.is_absolute():
        target = p.resolve()
    else:
        target = (Path(config_path).resolve().parent / p).resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def resolve_reference_file(
    name: str = 'cycle_reference_default.npz',
    test_space_dir: str | Path | None = None,
) -> Path:
    test_space = resolve_test_space_dir(test_space_dir)
    ref_dir = (test_space / 'reference_data').resolve()
    ref_dir.mkdir(parents=True, exist_ok=True)
    return ref_dir / name
