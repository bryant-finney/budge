---
name: pydantic-model-notes
description: budge pydantic model gotchas — field docstrings leak into OpenAPI, strict mode vs the frozenset serializer, FiniteFloat, models.py must stay a leaf
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
- **Lax mode coerces** (`amount='28.34'` becomes `28.34`, `pending='yes'` becomes `True`). `strict=True` was measured
  on 2026-10-18 and broke 7 tests: the factories rebuild from python-mode `model_dump()`, which emits the sorted
  `list` for `recurring_outflow_ids`, and strict mode rejects a list for a `frozenset` (JSON input is still fine).
  Raised on PR #23 as a maintainer decision; not adopted yet.

Related: [[lambda-logging-format]].
