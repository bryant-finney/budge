---
name: compose-layering
description: Owner design decision for local development - root compose.yaml is the minimal rel definition, and dev extras live in etc/compose/targets/dev.yaml, selected by COMPOSE_FILE; includes how its paths and merges resolve
metadata:
  type: project
---

# Compose layering for local development

Decided by the owner on PR #34, 2026-11-03: "the root `compose.yaml` should define the minimal content needed to run the
`rel` image targets", and `dev`'s "volume mounts, commands, entrypoints, the `dev` build target, etc." go in
`etc/compose/targets/dev.yaml`, selected through `COMPOSE_FILE`. The owner asked for this to be remembered as an explicit
design decision for local development.

**Why:** the root file then describes what ships, with no conditionals, and `dev` is a visible, additive layer. It
replaced `extends.file: etc/compose/targets/${BUDGE_BUILD_TARGET:-dev}.yaml`.

**How to apply:**

- `compose.yaml` sets no `target`, so builds use the Containerfile's last stage, `rel`, which has to stay last. `dev.yaml`
  hardcodes `target: dev`, and it also has to override `image`, or `dev` builds overwrite the `rel` tag.
- Don't reintroduce a target variable or a `rel` overlay. Settings only `dev` needs go in `dev.yaml`.
- `etc/base.env` sets `COMPOSE_FILE=compose.yaml:etc/compose/targets/dev.yaml`, and `.envrc` adds it only to a `.env` with
  no `COMPOSE_FILE`. Never overwrite an existing value: `COMPOSE_FILE=compose.yaml` is how someone stays on `rel`.
- Docker Compose v5.6.1 behaviour, checked 2026-11-03:
  - Relative paths in `dev.yaml` resolve from the first listed file's directory, so its mount source is `./src/back-end`.
    Read the rendered `source` in `docker compose config`, because `config -q` passes for a wrong path.
  - `healthcheck.test` in an overlay replaces the base's list, while the base's `interval`, `retries` and `timeout` stay.
  - `-f` beats `COMPOSE_FILE`.
  - A relative `COMPOSE_FILE` resolves from the current directory, so under direnv `docker compose` fails from
    `src/back-end` with `compose file "compose.yaml" set by COMPOSE_FILE environment variable is invalid`. Run it from
    the repository root.
- The `.env` in a checkout now selects dev mode, so see [[compose-env-file-autoload]] when rendering `rel`.
- direnv exports `.env` into the shell, and that beats the file: a stale `COMPOSE_FILE` or `BUDGE_*` can make a test pass
  or fail for the wrong reason. Run Compose under `env -i` to test what `.env` itself does.
