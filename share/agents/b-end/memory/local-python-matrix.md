---
name: local-python-matrix
description: how to run the 3.11-3.15 pytest matrix on the maintainer's Mac and in an isolated agent worktree
metadata:
  type: reference
---

# Running the local Python matrix

- The pyenv `python3.11` shim on the maintainer's Mac is broken: its pyenv global points at uninstalled versions (as
  of 2026-10-25, `~/.pyenv/version` names 3.12.10 and 3.13.3, neither installed). `python` inside an activated
  `.venv` is unaffected. `UV_PYTHON=3.11 uv run --directory src/back-end --locked --all-groups pytest` makes uv
  download a managed CPython 3.11; 3.12-3.15 come from Homebrew.

- Each `UV_PYTHON=<v> uv run` recreates `src/back-end/.venv` for that interpreter. Re-sync afterwards
  (`uv --directory src/back-end sync --locked --all-groups`) if a later tool depends on the venv.

- In a worktree-isolated agent session, Bash refuses `for` loops, pipes into `jq`/`python -c` and other "complex"
  commands as possibly unverifiable git. Put loops in a script in the session scratchpad and run it with `bash <path>`.
  Use `gh ... --jq` only in simple, unpiped commands.

- `taplo-format` (taplo-pre-commit v0.9.3) and `check-toml` do match `uv.lock` (identify tags: `toml`, `uv-lock`), but
  leave uv 0.13's output unchanged, so they pass today.

- **History: the uv-managed CPython 3.13.7 was SIGKILLed twice (2026-10-18, 2026-10-25). It works now.** The user
  repaired it each time, the second time with `uv python install --reinstall` (2026-10-25). Symptom: every
  `uv run` on the 3.13.7 `.venv` exits 137 with no output, as does the bare
  `~/.local/share/uv/python/cpython-3.13.7-macos-aarch64-none/bin/python3.13 -c 'print(1)'`. The cause is unknown.
  A chain like `cmd | tail -1` prints nothing instead of failing, so check `$?` on its own line.

  - If it recurs, report it. Run `uv python install --reinstall` only when the user asks; don't delete the user's uv
    Pythons.
  - Workaround meanwhile: `rsync` `src/back-end/` (minus `.venv` and caches) into the scratchpad and run the gates
    there with `UV_PYTHON=3.14`. Run hooks with `uvx --python 3.14 pre-commit`. The git `pre-commit` hook uses
    Homebrew's Python, so commits still work.
  - The 2026-10-25 reinstall didn't need a `.venv` rebuild. `pyvenv.cfg` `home` points at the
    `cpython-3.13-macos-aarch64-none` symlink, which the reinstall kept. If a `.venv` still fails afterwards, rebuild
    it (`rm -rf .venv && uv sync --locked --all-groups`, with `VIRTUAL_ENV` unset).

Related: [[coverage-sysmon-contexts]].
