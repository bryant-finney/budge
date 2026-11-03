# Back-end containers

From the repository root, these commands start the API and persistent MinIO. On the default `dev` target, the API
runs uvicorn with reload against the checkout mounted at `/workspace`:

```sh
direnv allow
docker compose up --build --wait
docker compose run --rm api uv run --frozen pytest
docker compose down
```

`.envrc` seeds `.env` from `etc/base.env` and refreshes `BUDGE_VERSION`, `BUDGE_IMAGE_VERSION`, and
`BUDGE_GIT_COMMON_DIR`.
The root `pyproject.toml` configures `uv-dynamic-versioning`; its CLI resolves the latest matching Git tag
without installing the back end. Direnv watches Git HEAD, the branch ref, and release tags to refresh the
version after Git changes; `direnv reload` forces a refresh. With plain Bash, use
`source .envrc` instead. `.env` stays ignored, and other local values are preserved. Change local ports,
image prefix, architecture, or MinIO development credentials there. Endpoints stay in Compose service
environments, so they cannot redirect host AWS/Pulumi commands. Services publish no host ports by default.
Compose names each stack after its checkout directory, so differently named worktrees can run concurrently
with separate networks and data volumes. Set `COMPOSE_PROJECT_NAME` in `.env` or pass `docker compose -p <name>`
to choose a project name explicitly. MinIO data stays in its named volume after `down`.

Compose finds `compose.yaml` by itself, so `etc/base.env` doesn't set `COMPOSE_FILE`. To expose the API, Lambda
emulator, and MinIO on the host, set `COMPOSE_FILE=compose.yaml:etc/compose/ports.yaml` in `.env`, then run:

```sh
docker compose --profile lambda up --build --wait
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:9002/2015-03-31/functions/function/invocations -d '{}'
```

The ports overlay binds only to loopback by default. The `api` container listens on port 8080 on both build targets.
MinIO's console is at `http://127.0.0.1:9001`.
Use `BUDGE_BIND_HOST`, `BUDGE_API_PORT`, `BUDGE_INGESTION_PORT`, `MINIO_API_PORT`, and `MINIO_CONSOLE_PORT`
in `.env` to configure these bindings; choose different host ports when exposing concurrent stacks.

Both image builds run `uv-dynamic-versioning` against the checkout's Git history without a version override.
The build context is the repository root; `.dockerignore` excludes local environments, credentials, caches,
and Git metadata, keeping only an empty root `.git` entry. Compose supplies the common Git directory
(`BUDGE_GIT_COMMON_DIR`, resolved by `.envrc`) as a read-only named build context, because a linked worktree's `.git`
is a file pointing outside the build context. The build reads that file to find the worktree's directory under the
common one, so it versions the worktree's own HEAD. Only the build commands mount these; neither image retains Git
metadata.
Images are `ghcr.io/bryant-finney/dev/budge:<version>` and `ghcr.io/bryant-finney/rel/budge:<version>`.
Release versions such as `1.2.3` are unchanged; development versions replace `+` with `-` in the OCI tag only,
because OCI tags cannot contain `+`. The installed package retains the exact version.
The image version falls back from `BUDGE_IMAGE_VERSION` to `BUDGE_VERSION`, then `0.0.0`; an explicit
`BUDGE_IMAGE_VERSION` environment variable overrides the generated value. Existing `.env` files keep local
settings while `.envrc` replaces the old generated `BUDGE_IMAGE_TAG` with `BUDGE_IMAGE_VERSION`, drops the old
generated `BUDGE_GIT_DIR` and `BUDGE_REPO_ROOT`, and removes the former overlay paths `etc/compose/dev.yaml` and
`etc/compose/volumes.yaml` from `COMPOSE_FILE`. It also deletes `COMPOSE_FILE` when only `compose.yaml` remains.

The default `dev` image has source, tests, uv, Git, Node, and development tools, and installs the back end in editable
mode from `/workspace/src/back-end`. `etc/compose/targets/dev.yaml` mounts the checkout there, so `api` runs the
checkout's source and uvicorn reloads on an edit. It also mounts the Git common directory read-only into `api` at its
real absolute path, which a linked worktree's `.git` file names. `uv run` rebuilds the editable install from Git's
version and writes it to `budge/_version.py` in the checkout; without Git, it would write `0.0.0`. `ingestion` gets
`src/back-end` read-only, and picks up source edits after `docker compose restart ingestion`. The virtual environment
stays at `/opt/budge`, with its tools on `PATH`.
`podman compose …` uses a compatible Compose provider. No Docker-only runtime attributes are required. The build
files are `src/back-end/Containerfile` and `src/minio/Containerfile`.

## Build targets

`BUDGE_BUILD_TARGET` selects the build target and image namespace of both `api` and `ingestion`, which share one image
per target; unset, it's `dev`. It's the only setting a target needs, with or without the ports overlay:
`BUDGE_BUILD_TARGET=rel docker compose up --build --wait` runs the lean image. Compose reads `api`'s settings from
`etc/compose/targets/<target>.yaml`, so any other value fails with a `no such file or directory` error. Don't list a
target file in `COMPOSE_FILE`: its settings would apply on every target, and its relative mount sources would resolve
from the project directory instead of the file's own.

| Service                        | `dev`                                              | `rel`                                               |
| ------------------------------ | -------------------------------------------------- | --------------------------------------------------- |
| `api`                          | uvicorn serving HTTP                               | Lambda emulator running `budge.api.handler.handler` |
| `ingestion` (`lambda` profile) | Lambda emulator running the source in `/workspace` | Lambda emulator running the installed wheel         |

`rel` has no development ASGI server, so its `api` answers Lambda invocations rather than HTTP routes. Send it an
API Gateway event:

```sh
curl -X POST http://127.0.0.1:8000/2015-03-31/functions/function/invocations \
  -d @src/back-end/tests/events/apigw-v2-get-health.json
```

On `rel`:

- Every other path returns 404, including `/api/health`, so the Vite proxy can't reach the API. Use `dev` for front-end
  work.
- Source edits need a rebuild. There's no reload, and nothing is mounted.
- There's no uv, pytest, or Git, so `docker compose run --rm api uv run …` fails.

The emulator handles one invocation at a time on either target. Overlapping invocations crash it, and the container
exits with code 2. For that reason, the `rel` health check calls the handler only until it passes, then just checks
that the emulator is listening.

`etc/compose/targets/<target>.yaml` hardcodes `api`'s command, and `compose.yaml` hardcodes `ingestion`'s handler. On
`rel`, both use the Lambda base image's `/lambda-entrypoint.sh`. The `dev` image clears that entry point, so `api` runs
uvicorn directly, and `etc/compose/targets/dev.yaml` sets it again for `ingestion`.

## Images

Both builds use standard Compose fields. Docker can delegate to Buildx (`COMPOSE_BAKE=true`), or read the resolved
configuration directly; other providers ignore the optional `x-bake` local-output hint:

```sh
docker compose --profile lambda config | docker buildx bake -f - --load api ingestion minio
docker compose --profile lambda up --build --wait
```

`ingestion` runs the Lambda Runtime Interface Emulator through the base image's `/lambda-entrypoint.sh` on both
targets. The `dev` stage sets `LAMBDA_TASK_ROOT` and `PYTHONPATH` so the runtime finds the source and the virtual
environment's packages; `rel` needs neither, because its packages are in `/var/task`. The `rel` image's default handler
is `budge.ingestion.handler.handler`; the API Lambda selects `budge.api.handler.handler`. No development tools or
Git metadata are baked into `rel`. MinIO is built from an immutable upstream source commit: the community edition
is [source-only](https://github.com/minio/minio#source-only-distribution), and historical official image tags are
unavailable. Its first build downloads Go dependencies and compiles the server; subsequent builds reuse that layer.

Dependabot updates the tag and digest on each Containerfile's upstream `FROM` lines. Everything else is a manual
bump: `MINIO_COMMIT` (both `ARG` defaults and the `compose.yaml` default), `MINIO_RELEASE` in `compose.yaml`, the
release named in the MinIO Containerfile's comment, and the `microdnf` package versions. Upstream `minio/minio` is
archived and the pinned commit is its last release, so there's no newer MinIO release to move to.

The current API/AWS adapters are skeletons: this stack verifies health, source reload (on `dev`), and S3 availability;
Secrets Manager seeding and application storage wiring remain milestone 2 work.
MinIO enforces conditional writes but ignores `DeleteObject`'s `If-Match`: the future lease adapter must use the
owner re-check fallback described in design spec §12 for local lease release.
