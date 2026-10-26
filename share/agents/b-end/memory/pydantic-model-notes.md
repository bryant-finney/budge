---
name: pydantic-model-notes
description: budge pydantic model gotchas — field docstrings leak into OpenAPI, strict mode and python-mode dumps, FiniteFloat, models.py must stay a leaf
metadata:
  type: reference
---

# Pydantic model notes (`budge/models.py`)

- **`use_attribute_docstrings=True` turns every field docstring into a JSON-schema / OpenAPI `description`.** Keep
  field docstrings user-facing. Put implementation rationale and open spec questions in `#` comments above the
  field (done for `Transaction.amount` / `currency`, 2026-10-18).
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
