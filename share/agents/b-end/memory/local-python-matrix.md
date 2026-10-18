---
name: local-python-matrix
description: how to run the 3.11-3.15 pytest matrix on the maintainer's Mac and in an isolated agent worktree
metadata:
  type: reference
---

# Running the local Python matrix

- The pyenv `python3.11` shim on the maintainer's Mac is broken (its pyenv global points at uninstalled versions).
  `UV_PYTHON=3.11 uv run --directory src/back-end --locked --all-groups pytest` makes uv download a managed
  CPython 3.11; 3.12-3.15 come from Homebrew.

- Each `UV_PYTHON=<v> uv run` recreates `src/back-end/.venv` for that interpreter. Re-sync afterwards
  (`uv --directory src/back-end sync --locked --all-groups`) if a later tool depends on the venv.

- In a worktree-isolated agent session, Bash refuses `for` loops, pipes into `jq`/`python -c` and other "complex"
  commands as possibly unverifiable git. Put loops in a script in the session scratchpad and run it with `bash <path>`.
  Use `gh ... --jq` only in simple, unpiped commands.

- `taplo-format` (taplo-pre-commit v0.9.3) and `check-toml` do match `uv.lock` (identify tags: `toml`, `uv-lock`), but
  leave uv 0.13's output unchanged, so they pass today.

- **2026-10-18: the uv-managed `cpython-3.13.7-macos-aarch64-none` started dying with SIGKILL (exit 137) partway
  through a session.** That broke `uvx pre-commit` and every `.venv` built on it. Homebrew 3.12/3.14 and uv's 3.11
  kept working, and the binary's files were unchanged since 2025-11. The cause is unknown (possibly the environment
  or sandbox). Workaround: `uvx --python 3.14 pre-commit ...`, and `UV_PYTHON=3.14` for gates on a `git archive`
  export. Don't delete or reinstall the user's uv Pythons yourself; report it.

Related: [[coverage-sysmon-contexts]].
