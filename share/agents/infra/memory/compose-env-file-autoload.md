---
name: compose-env-file-autoload
description: docker compose auto-loads .env from the project directory even under env -i, so clean renders need a directory without one
metadata:
  type: project
---

# Compose reads `.env` under `env -i`

`env -i` only clears the process environment. `docker compose` still loads `.env` from the project
directory, so a worktree's stale `.env` changes the render.

**Why:** On PR #34 (2026-11-03) a render from the worktree under `env -i` showed the image tag
`0.0.1.dev201-7d20968` and a different `git-common` path, while the same files without `.env` gave
`0.0.0`. The difference looked like a change in `compose.yaml`.

**How to apply:** To compare two revisions, export `compose.yaml` and `etc/compose/` to one scratch
directory with no `.env`, render, swap in the other `compose.yaml`, render again, and compare bytes.
Using one directory also keeps absolute paths equal, so no normalizing is needed. See
[[compose-target-extends]] for testing what a fresh `.env` does.
