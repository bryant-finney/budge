"""Smoke tests: the package imports, its metadata is consistent, and the sdist and wheel ship only the package."""

import importlib
import importlib.metadata
import importlib.resources
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

import budge

SUBPACKAGES: tuple[str, ...] = (
    'budge.api',
    'budge.aws',
    'budge.classify',
    'budge.ingestion',
    'budge.plaid_client',
    'budge.storage',
)


@pytest.mark.parametrize('name', ['budge', *SUBPACKAGES])
def test_package_imports_with_docstring(name: str) -> None:
    """Each package imports and documents its responsibility in a module docstring."""
    module: ModuleType = importlib.import_module(name)

    assert module.__name__ == name
    assert module.__doc__
    assert module.__doc__.strip()


def test_version_matches_distribution_metadata() -> None:
    """`budge.__version__` is the installed distribution's version."""
    assert budge.__version__ == importlib.metadata.version('budge')


def test_generated_version_module_matches_distribution_metadata() -> None:
    """The build hook writes `budge/_version.py` for editable installs too, with the distribution's version."""
    version_module: ModuleType = importlib.import_module('budge._version')

    assert version_module.__version__ == importlib.metadata.version('budge')


def test_version_falls_back_without_generated_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the build-generated `budge/_version.py`, `__version__` is `'0.0.0'`.

    That's the case when only the committed `budge/` source is copied into an image.
    """
    # a `None` entry in `sys.modules` makes `import budge._version` raise `ModuleNotFoundError`
    monkeypatch.setitem(sys.modules, 'budge._version', None)
    try:
        assert importlib.reload(budge).__version__ == '0.0.0'
    finally:
        # restore `budge._version` and re-run `budge/__init__.py` so later tests see the installed version
        monkeypatch.undo()
        importlib.reload(budge)

    assert budge.__version__ == importlib.metadata.version('budge')


def test_package_is_typed() -> None:
    """The package ships a PEP 561 `py.typed` marker."""
    assert importlib.resources.files('budge').joinpath('py.typed').is_file()


BACK_END_SOURCES: tuple[str, ...] = ('.envrc', 'budge', 'conftest.py', 'pyproject.toml', 'tests', 'uv.lock')
"""The tracked top-level entries of `src/back-end/`, copied into the source tree that `built_distributions` builds."""


@pytest.fixture(scope='module')
def built_distributions(pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the sdist, and the wheel from it, as `uv build` does, from a copy of the back end; return the out dir.

    Building a copy leaves the checkout's generated `budge/_version.py` alone. The copy has no `.git`, so nothing is
    gitignored there and the version is the `fallback-version`. `--offline` keeps the run hermetic: the build backend
    is already in uv's cache from the editable install that `uv run`/`uv sync` built.
    """
    source: Path = tmp_path_factory.mktemp('source')
    for name in BACK_END_SOURCES:
        path: Path = pytestconfig.rootpath / name
        if path.is_dir():
            shutil.copytree(path, source / name, ignore=shutil.ignore_patterns('__pycache__', '_version.py'))
        else:
            shutil.copy2(path, source / name)

    uv: str | None = shutil.which('uv')
    assert uv is not None, '`uv` must be on PATH to build the distributions'
    out_dir: Path = tmp_path_factory.mktemp('dist')
    subprocess.run(  # noqa: S603 (trusted: the `uv` executable on PATH and paths this fixture created)
        [uv, 'build', '--offline', '--quiet', '--out-dir', str(out_dir), str(source)],
        check=True,
        capture_output=True,
    )
    return out_dir


def test_sdist_ships_only_the_package(built_distributions: Path) -> None:
    """The sdist holds `budge/` and build metadata, not the rootdir `conftest.py`, `tests/`, `.envrc` or `uv.lock`."""
    (sdist,) = built_distributions.glob('*.tar.gz')
    with tarfile.open(sdist) as archive:
        # drop the `budge-<version>/` prefix
        names: set[str] = {member.name.partition('/')[2] for member in archive.getmembers()}

    assert {name.partition('/')[0] for name in names} == {'PKG-INFO', 'budge', 'pyproject.toml'}
    assert 'budge/_version.py' in names


def test_wheel_ships_only_the_package(built_distributions: Path) -> None:
    """The wheel holds `budge/` (with the generated `_version.py`) and its `.dist-info`, nothing else."""
    (wheel,) = built_distributions.glob('*.whl')
    with zipfile.ZipFile(wheel) as archive:
        names: list[str] = archive.namelist()

    top_level: set[str] = {name.partition('/')[0] for name in names}
    assert {entry for entry in top_level if not entry.endswith('.dist-info')} == {'budge'}
    assert 'budge/_version.py' in names
