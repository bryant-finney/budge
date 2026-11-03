---
name: compose-target-extends
description: Compose can vary a service's defaults by a variable through an interpolated extends.file; extends.file resolves from the project directory, but relative volume sources in the extended file don't
metadata:
  type: reference
---

# Vary Compose defaults through `extends.file`

Compose has no conditionals, but `extends.file` is interpolated before it loads, so
`file: etc/compose/targets/${BUDGE_BUILD_TARGET:-dev}.yaml` selects a whole set of per-target
defaults. Checked with Docker Compose v5.6.1 on 2026-11-03; native Podman wasn't tested.

- A relative `extends.file` resolves from the project directory, even in an overlay under
  `etc/compose/`.
- A relative volume `source` inside the extended file resolves from that file's directory, so
  `etc/compose/targets/dev.yaml` needs `../../..` for the repository root. `${VAR:-.}` silently mounts
  `etc/compose/targets/`. Read the rendered source in `docker compose config`, because `config -q` passes
  either way.
- Listing that same file in `COMPOSE_FILE` resolves its sources from the project directory, so `../../..`
  mounts a directory outside the checkout. Its `command` also overrides every target, whichever file
  `extends` chose. A target file has to come only through `extends`.
- A partial `healthcheck` merges with the extending service's, and an empty `service: {}` is a valid
  no-op target.
- direnv exports `.env` into the agent's shell, and that beats the file: a stale `COMPOSE_FILE` or
  `BUDGE_*` can make a test pass or fail for the wrong reason. Run Compose under `env -i` with
  `--env-file` to test what a fresh `.env` does.
