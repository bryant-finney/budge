"""The Lambda handler strings infra deploys resolve to callables (spec §4; issue #4's contract with infra)."""

import importlib

import pytest


@pytest.mark.parametrize('handler_string', ['budge.api.handler.handler', 'budge.ingestion.handler.handler'])
def test_lambda_handler_string_resolves(handler_string: str) -> None:
    """Resolve the string as the Python runtime interface client does: split on the last `.`, import, getattr."""
    module_name, _, attribute = handler_string.rpartition('.')

    handler: object = getattr(importlib.import_module(module_name), attribute)

    assert callable(handler)
