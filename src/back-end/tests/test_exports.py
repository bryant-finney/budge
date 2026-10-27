"""Every `budge` module declares `__all__`, and it lists every public name the module defines.

Type checkers only need re-exports listed, but documentation generators (pdoc, Sphinx autodoc, mkdocstrings) document
only what `__all__` names, so a definition left out is missing from the API docs. Modules are read with `ast`, not
imported, so the check sees each binding as written, including both branches of a `try`/`except` fallback. Imported
names are optional: a module lists the ones it re-exports. A module-level logger bound with `getLogger(...)` is exempt:
it is module infrastructure that callers reach by name through `logging`, never by import, so it is not API to document.
"""

import ast
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest

import budge

PACKAGE_DIR: Path = Path(budge.__file__).parent
"""The `budge` package source directory (an editable install, so this is the working tree)."""

MODULES: tuple[Path, ...] = tuple(sorted(path for path in PACKAGE_DIR.rglob('*.py') if path.name != '_version.py'))
"""Every module and package `__init__.py` under `budge/`, except the build-generated `_version.py`."""

MODULE_HOOKS: frozenset[str] = frozenset({'__all__', '__dir__', '__getattr__'})
"""Dunder names Python itself reads from a module; they are never listed in `__all__`."""


def module_id(path: Path) -> str:
    """Name a parametrized case by its path from the package's parent, e.g. `budge/aws/repository.py`."""
    return path.relative_to(PACKAGE_DIR.parent).as_posix()


def parse(path: Path) -> ast.Module:
    """Parse the module at `path` without importing it."""
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


def module_level_statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Yield each statement in `body`, descending into `if` and `try` blocks but not into `def` or `class` scopes."""
    for node in body:
        yield node
        if isinstance(node, ast.If):
            yield from module_level_statements(node.body + node.orelse)
        elif isinstance(node, ast.Try | ast.TryStar):
            handled = [stmt for handler in node.handlers for stmt in handler.body]
            yield from module_level_statements(node.body + handled + node.orelse + node.finalbody)


def target_names(target: ast.expr) -> Iterator[str]:
    """Yield the names an assignment target binds: `x`, or each name in `x, (y, *z)`; attributes bind none."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Tuple | ast.List):
        for element in target.elts:
            yield from target_names(element)
    elif isinstance(target, ast.Starred):
        yield from target_names(target.value)


def assignment_targets(node: ast.stmt) -> list[ast.expr]:
    """Return the targets an assignment or PEP 695 `type` alias binds; `[]` for any other statement."""
    if isinstance(node, ast.Assign):
        return node.targets
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if sys.version_info >= (3, 12) and isinstance(node, ast.TypeAlias):
        return [node.name]
    return []


def assigned_value(node: ast.stmt) -> ast.expr | None:
    """Return the value an assignment binds; `None` for an annotation-only declaration or any other statement."""
    return node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None


def is_logger_binding(node: ast.stmt) -> bool:
    """Whether the statement binds a logger: its value is a `getLogger(...)` call, e.g. `logging.getLogger(__name__)`.

    The rule matches the callee's name, so `from logging import getLogger` works too, and never the bound name, so a
    constant called `logger` is still listed.
    """
    value = assigned_value(node)
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    return (isinstance(func, ast.Attribute) and func.attr == 'getLogger') or (
        isinstance(func, ast.Name) and func.id == 'getLogger'
    )


def defined_names(node: ast.stmt) -> Iterator[str]:
    """Yield the names a statement defines: a class, a function, or assignment targets other than a logger.

    Imports define none here.
    """
    if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        yield node.name
    if is_logger_binding(node):
        return
    for target in assignment_targets(node):
        yield from target_names(target)


def is_public(name: str) -> bool:
    """Whether `name` belongs in `__all__`: not `_private`, though a dunder such as `__version__` does."""
    is_dunder = name.startswith('__') and name.endswith('__')
    return name not in MODULE_HOOKS and (is_dunder or not name.startswith('_'))


def public_definitions(tree: ast.Module) -> set[str]:
    """Return the public names the module defines at module level."""
    return {name for node in module_level_statements(tree.body) for name in defined_names(node) if is_public(name)}


def declared_all(tree: ast.Module) -> list[str] | None:
    """Return the module's `__all__` if it is a top-level literal list or tuple of strings, else `None`."""
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign) or node.value is None:
            continue
        if any(isinstance(target, ast.Name) and target.id == '__all__' for target in assignment_targets(node)):
            return literal_strings(node.value)
    return None


def literal_strings(value: ast.expr) -> list[str] | None:
    """Return the strings in a literal list or tuple of string constants, else `None`."""
    if not isinstance(value, ast.List | ast.Tuple):
        return None
    elements = [element.value for element in value.elts if isinstance(element, ast.Constant)]
    strings = [element for element in elements if isinstance(element, str)]
    return strings if len(strings) == len(value.elts) else None


def test_modules_are_discovered() -> None:
    """The parametrized checks below cover the package, so they can't pass vacuously on an empty module list."""
    assert PACKAGE_DIR / '__init__.py' in MODULES
    assert PACKAGE_DIR / 'storage' / 'repository.py' in MODULES
    assert PACKAGE_DIR / '_version.py' not in MODULES


@pytest.mark.parametrize('path', MODULES, ids=module_id)
def test_module_declares_all(path: Path) -> None:
    """The module defines `__all__` as a literal list or tuple of strings, so tools can read it without importing."""
    assert declared_all(parse(path)) is not None, (
        f'{module_id(path)} must define `__all__` as a literal list or tuple of strings'
    )


@pytest.mark.parametrize('path', MODULES, ids=module_id)
def test_all_lists_every_public_definition(path: Path) -> None:
    """Every public class, function, constant, and type alias the module defines is listed in its `__all__`."""
    tree = parse(path)

    missing = sorted(public_definitions(tree) - set(declared_all(tree) or ()))

    assert not missing, f'{module_id(path)}: add {missing} to `__all__` (or rename them `_private`)'


def test_public_definitions_finds_every_binding_form() -> None:
    """The walker finds each binding form, in `if` and `try` blocks too, and skips private, nested and logger names."""
    tree = ast.parse(
        textwrap.dedent(
            """
            import logging
            import os
            from typing import Final
            class Model: field = 1
            def function(): local = 1
            async def coroutine(): ...
            CONSTANT: Final = 1
            FIRST, (SECOND, *REST) = 1, (2, 3)
            OBJ.attribute = _private = __dunder__ = 1
            logger = logging.getLogger(__name__)
            def __getattr__(name): ...
            if os.name:
                BRANCH = 1
            else:
                ORELSE = 1
            try:
                from os import sep as TRIED
            except ImportError:
                TRIED = None
            else:
                TRY_ELSE = 1
            finally:
                FINALLY = 1
            __all__ = ['Model']
            """
        )
    )

    assert public_definitions(tree) == {
        'BRANCH',
        'CONSTANT',
        'FINALLY',
        'FIRST',
        'Model',
        'ORELSE',
        'REST',
        'SECOND',
        'TRIED',
        'TRY_ELSE',
        '__dunder__',
        'coroutine',
        'function',
    }


@pytest.mark.skipif(sys.version_info < (3, 12), reason='PEP 695 `type` statements need Python 3.12')
def test_public_definitions_finds_type_aliases() -> None:
    """A PEP 695 `type` alias is a definition, listed like any other."""
    assert public_definitions(ast.parse('type Alias = int\ntype _Private = str')) == {'Alias'}


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('logger = logging.getLogger(__name__)', set[str]()),
        ("log: logging.Logger = logging.getLogger('budge')", set[str]()),
        ('logger = getLogger(__name__)', set[str]()),
        ('if DEBUG:\n    logger = logging.getLogger(__name__)', set[str]()),
        ('logger = make_logger(__name__)', {'logger'}),
        ('logger = logging.Logger(__name__)', {'logger'}),
        ('LEVEL = logging.INFO', {'LEVEL'}),
        ('logger: logging.Logger', {'logger'}),
        ('LOGGERS = [logging.getLogger(__name__)]', {'LOGGERS'}),
    ],
)
def test_public_definitions_exempts_only_logger_bindings(source: str, expected: set[str]) -> None:
    """A `getLogger(...)` call is what exempts a binding, not the name it is bound to; other names are still listed."""
    assert public_definitions(ast.parse(source)) == expected


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ("__all__ = ['A', 'B']", ['A', 'B']),
        ("__all__: tuple[str, ...] = ('A',)", ['A']),
        ('__all__: list[str] = []', []),
        ("__all__ = ['A', NAME]", None),
        ("__all__ = 'A'", None),
        ("__all__: list[str]\n__all__ = ['A']", ['A']),
        ('__all__: list[str]', None),
        ('A = 1', None),
    ],
)
def test_declared_all_accepts_only_literal_string_sequences(source: str, expected: list[str] | None) -> None:
    """Only an assigned literal list or tuple of strings counts; a computed or annotation-only `__all__` does not."""
    assert declared_all(ast.parse(source)) == expected
