# infra memory

Index of infra agent memories, one line per entry.

- [Comments sparingly](comments-sparingly.md) — readable code/CI over explanatory comments; comment only what code can't say
- [Config validation gotchas](config-validation-gotchas.md) — ICU vs IANA zone names, Intl over-acceptance, Scheduler rate units
- [Commit hook prefix](git-commit-hook-gotchas.md) — prepare-commit-msg prepends `feat(#n):` (amends too); omit it, set `GIT_SKIP_OWNER_NAME=1`
- [pnpm/Node tooling gotchas](pnpm-node-tooling-gotchas.md) — pnpm 12 lockfile vs check-yaml, nodenv vs `.node-version`, skeleton packages, coverage proofs
- [Pulumi mock test harness](pulumi-mock-test-harness.md) — drain `setMocks` RPCs with `runtime.disconnect()` before asserting resources
- [Restacking across worktrees](git-worktree-restack.md) — `--update-refs` can't move a branch checked out in another worktree; use `--onto`
- [CI workflow gotchas](ci-node-setup.md) — pnpm before setup-node, uvx needs setup-uv, colons in run scalars, bot/GITHUB_TOKEN can't read admin settings
- [Isolated agent worktrees](agent-worktree-isolation.md) — can't use other worktrees; stack branches in one; one plain command per Bash call
- [Required checks: one aggregator](required-checks-aggregator.md) — require only `ci-ok` (always(), skipped=fail), never per-matrix contexts
- [YAML key order](yaml-key-order.md) — sort object keys alphabetically; workflows lead with `name`, `on`, `permissions`; lists keep order
- [Dependabot docker cooldown](dependabot-docker-cooldown.md) — publication dates come only from Docker Hub; compare digests before moving an image
- [Full Docker disk stops MinIO](docker-disk-full-minio.md) — "drive path full" means check `df` in a container; never prune the shared daemon
- [Compose layering](compose-layering.md) — owner decision: `compose.yaml` is minimal `rel`; `dev` extras in `etc/compose/targets/dev.yaml` via `COMPOSE_FILE`
- [Version source of truth](version-source-of-truth.md) — owner decision: `budge.__version__`, written by direnv; no version build args
- [Dev image has no uv or Git](dev-image-no-uv-or-git.md) — owner decision: version comes from the host, dev's metadata is 0.0.0; run tools directly
- [Lambda emulator overlap crash](lambda-rie-overlap-crash.md) — overlapping invocations kill the container; handler failures can still return HTTP 200
- [Justify every suppression](suppression-justification.md) — inline suppressions record why; yamllint rejects trailing text, so the reason goes above
- [PR body round trips](gh-pr-body-trailing-newline.md) — `gh pr view --jq .body` adds a newline that `--body-file` stores; PATCH JSON or strip it
- [Compose reads `.env` under `env -i`](compose-env-file-autoload.md) — clean renders need a directory without `.env`; compare bytes from one directory
