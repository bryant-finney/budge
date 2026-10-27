---
name: pydantic-model-notes
description: budge pydantic/OpenAPI gotchas — field and route-function docstrings leak into OpenAPI (routes pass description=), strict mode and python-mode dumps, FiniteFloat, models.py must stay a leaf
metadata:
  type: reference
---

# Pydantic model and OpenAPI notes (`budge/models.py`, `budge/api/`)

- **`use_attribute_docstrings=True` turns every field docstring into a JSON-schema / OpenAPI `description`.** Keep
  field docstrings user-facing. Put implementation rationale and open spec questions in `#` comments above the
  field (done for `Transaction.amount` / `currency`, 2026-10-18).
- **A path operation function's docstring becomes the operation's OpenAPI `description`** (FastAPI 0.143,
  `fastapi/routing.py`: `description or inspect.cleandoc(endpoint.__doc__)`), so its doctest and any `Args:` /
  `Returns:` sections show up in Swagger UI and ReDoc. Routes pass an explicit reader-facing `description=` and keep
  the doctest in the docstring (`get_health`, 2026-10-27, PR #26). Not `\f`: FastAPI truncates at a form feed, but
  ruff's D301 flags the backslash and its `r"""` autofix silently makes it a literal `\f`. `description=''` is falsy
  and falls back to the docstring. `include_in_schema=False` routes (`budge.api.routes.docs`) never appear.
  `tests/api/test_health.py` checks every operation's description for docstring markers.
- **`budge.models` must import nothing from `budge`.** `ExcludedReason` is defined there and re-exported by
  `budge.classify`, so M2's `classify(txn: Transaction)` can import the models without a cycle.
  `tests/test_models.py::test_models_is_a_leaf_module` enforces it.
- **`amount: FiniteFloat`**: pydantic writes NaN to JSON as `null`, which then fails `model_validate_json`, so one
  bad row would make a connection's whole `transactions.json.gz` unreadable.
- **`DomainModel` is `strict=True`** (adopted 2026-10-20, PR #23), so python-mode input is never coerced
  (`amount='28.34'` and `pending='yes'` fail). A python-mode `model_dump()` does not round-trip: it emits the sorted
  `list` for `recurring_outflow_ids`, which strict mode rejects for a `frozenset`. JSON round-trips still pass. Build
  test models from typed field values (as `tests/factories.py` does), never from a python-mode dump.

Related: [[lambda-logging-format]].
