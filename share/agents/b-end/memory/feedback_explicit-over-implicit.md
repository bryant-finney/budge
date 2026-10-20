---
name: explicit-over-implicit
description: User rule "explicit is better than implicit" — protocol implementations subclass the protocol and mark methods @override; prefer declared intent over convention
metadata:
  type: feedback
---

# Explicit is better than implicit

Prefer explicit declarations of intent over implicit conventions. In budge, a class that implements a
`typing.Protocol` (`Repository`, `SecretStore`, `IngestionTrigger`) subclasses that protocol explicitly
(PEP 544 allows it) instead of relying on structural typing alone.

**Why:** the user asked for this directly (2026-10-20, PR #23 / issue #3). With structural typing only, the
one conformance check was a `list[Protocol]` assignment in `tests/test_protocols.py`, so signature drift was
reported far from the adapter. Subclassing moves the error to the class definition.

**How to apply:**

- Production implementations (`budge.aws.*`) subclass their protocol and decorate each protocol method with
  `typing_extensions.override` (`typing.override` needs 3.12; the floor is 3.11). `typing-extensions` is a
  direct dependency in `pyproject.toml`, not borrowed from pydantic's transitive pin — same principle.
- `@override` methods drop "See `X.y`" stand-in docstrings: ruff `D102` skips `@override` methods, and
  `inspect.getdoc` inherits the protocol's text. `__init__` stays undecorated and documented.
- mypy enforces it: `explicit-override` is in `enable_error_code`, so an override without `@override` fails.
  mypy and ty both report a drifted signature at the subclass (`invalid-method-override` in ty).
- Test fakes in `tests/fakes.py` may stay structural; `test_implementations_conform_to_protocols` is their check.
- Beyond protocols, apply the same rule: declare dependencies you import, name codes in suppressions, annotate
  rather than infer at boundaries, and write config down instead of relying on tool defaults.

Related: [[pyright-gotchas]], [[ruff-nested-config-first-party]].
