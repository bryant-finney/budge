---
name: compose-target-extends
description: Compose can vary a service's defaults by a variable through an interpolated extends.file, whose relative path resolves from the project directory
metadata:
  type: reference
---

# Vary Compose defaults through `extends.file`

Compose has no conditionals, but `extends.file` is interpolated before it loads, so
`file: etc/compose/targets/${BUDGE_BUILD_TARGET:-dev}.yaml` selects a whole set of per-target
defaults. Checked with Docker Compose v5.6.1 on 2026-11-02; native Podman wasn't tested.

- A relative `extends.file` resolves from the project directory, even in an overlay under
  `etc/compose/`. `targets/dev.yaml` from `etc/compose/volumes.yaml` fails with `no such file`.
- A partial `healthcheck` merges with the extending service's, and an empty `service: {}` is a valid
  no-op target.
- An overlay that sets `command` directly overrides every target, so anything target-specific in
  `etc/compose/volumes.yaml` has to come through `extends` too. The default `.env` includes that overlay,
  so testing only `compose.yaml` misses this.
