from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from motor_sim.config import load_config
from motor_sim.core.builder import ModelBuilder
from motor_sim.paths import build_paths, resolve_reference_file


@pytest.fixture(scope='session')
def code_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope='session')
def project_dir() -> Path:
    value = os.getenv('MOTORSIM_PROJECT_DIR')
    if not value:
        pytest.skip('MOTORSIM_PROJECT_DIR is not set.')
    return Path(value).expanduser().resolve()


@pytest.fixture(scope='session')
def test_space_dir() -> Path:
    value = os.getenv('MOTORSIM_TEST_SPACE')
    if not value:
        pytest.skip('MOTORSIM_TEST_SPACE is not set.')
    return Path(value).expanduser().resolve()


@pytest.fixture(scope='session')
def runtime_paths(project_dir: Path, test_space_dir: Path):
    return build_paths(project_dir=project_dir, test_space_dir=test_space_dir)


@pytest.fixture(autouse=True)
def _change_to_code_root():
    old_cwd = Path.cwd()
    os.chdir(PROJECT_ROOT)
    try:
        yield
    finally:
        os.chdir(old_cwd)


@pytest.fixture(scope='session')
def cfg(runtime_paths):
    return load_config(str(runtime_paths.project_dir / 'config.json'))


@pytest.fixture(scope='session')
def reference_file(runtime_paths) -> Path:
    return resolve_reference_file(test_space_dir=runtime_paths.test_space_dir)


@pytest.fixture()
def built_model(cfg):
    S, ctx, model, t_span, y0 = ModelBuilder(cfg).build()
    return {
        'S': S,
        'ctx': ctx,
        'model': model,
        't_span': t_span,
        'y0': y0,
        'cfg': cfg,
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    extra = getattr(report, 'extra', [])
    if report.when == 'call':
        extra.extend(getattr(item, '_html_extras', []))
    report.extra = extra
