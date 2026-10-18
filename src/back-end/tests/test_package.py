"""Smoke tests: the `budge` package and every subpackage import, and the package metadata is consistent."""

import importlib
import importlib.metadata
import importlib.resources
import sys
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
    """Without the build-generated `budge/_version.py` (e.g. only `budge/` copied into an image), `__version__` is
    `'0.0.0'`."""
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
