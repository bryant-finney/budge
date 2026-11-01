# Back-end containers

From the repository root, start the API and persistent MinIO with live source edits:

```sh
direnv allow
docker compose up --build --wait
docker compose run --rm api uv run --frozen pytest
docker compose down
```

`.envrc` seeds `.env` from `etc/base.env` and refreshes `BUDGE_VERSION`, `BUDGE_IMAGE_VERSION`, and checkout paths.
The root `pyproject.toml` configures `uv-dynamic-versioning`; its CLI resolves the latest matching Git tag
without installing the back end. Direnv watches Git HEAD, the branch ref, and release tags to refresh the
version after Git changes; `direnv reload` forces a refresh. With plain Bash, use
`source .envrc` instead. `.env` stays ignored, and other local values are preserved. Change local ports,
image prefix, architecture, or MinIO development credentials there. Endpoints stay in Compose service
environments, so they cannot redirect host AWS/Pulumi commands. Services publish no host ports by default.
Compose names each stack after its checkout directory, so differently named worktrees can run concurrently
with separate networks and data volumes. Set `COMPOSE_PROJECT_NAME` in `.env` or pass `docker compose -p <name>`
to choose a project name explicitly. MinIO data stays in its named volume after `down`.

To expose the API, Lambda emulator, and MinIO on the host, append `:etc/compose/ports.yaml` to `COMPOSE_FILE`
in `.env`, then run:

```sh
docker compose --profile lambda up --build --wait
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:9002/2015-03-31/functions/function/invocations -d '{}'
```

The ports overlay binds only to loopback by default. MinIO's console is at `http://127.0.0.1:9001`.
Use `BUDGE_BIND_HOST`, `BUDGE_API_PORT`, `BUDGE_INGESTION_PORT`, `MINIO_API_PORT`, and `MINIO_CONSOLE_PORT`
in `.env` to configure these bindings; choose different host ports when exposing concurrent stacks.

Both image builds run `uv-dynamic-versioning` against the checkout's Git history without a version override.
The build context is the repository root; `.dockerignore` excludes local environments, credentials, caches,
and Git metadata. Compose supplies the common Git directory as a read-only named build context.
`.envrc` resolves that directory and the relative worktree Git path (`.` in a normal clone).
Only the build commands mount this context; neither image retains Git metadata.
Images are `ghcr.io/bryant-finney/dev/budge:<version>` and `ghcr.io/bryant-finney/rel/budge:<version>`.
Release versions such as `1.2.3` are unchanged; development versions replace `+` with `-` in the OCI tag only,
because OCI tags cannot contain `+`. The installed package retains the exact version.
The image version falls back from `BUDGE_IMAGE_VERSION` to `BUDGE_VERSION`, then `0.0.0`; an explicit
`BUDGE_IMAGE_VERSION` environment variable overrides the generated value. Existing `.env` files keep local
settings while `.envrc` replaces the old generated `BUDGE_IMAGE_TAG` with `BUDGE_IMAGE_VERSION`.

The default `dev` image has source, tests, uv, Git, Node, and development tools. `COMPOSE_FILE` selects the
`etc/compose/dev.yaml` overlay, which mounts the checkout and read-only Git common directory at their real absolute
paths, including linked worktrees, and runs uvicorn with reload. The virtual environment stays at `/opt/budge`.
The base `docker compose -f compose.yaml …` also runs without this overlay. `podman compose …` uses a compatible
Compose provider. No Docker-only runtime attributes are required. `BUDGE_BUILD_TARGET` defaults to `dev` and
selects the API build target and matching image namespace. For example,
`BUDGE_BUILD_TARGET=rel docker compose -f compose.yaml build api` builds the Lambda image. The API service
and development overlay run `dev`; the lean `rel` image has no uv or development ASGI server. Use
`ingestion` for its Lambda emulator; that service always builds `rel`. The build files are
`src/back-end/Containerfile` and `src/minio/Containerfile`.

Both builds use standard Compose fields. Docker can delegate to Buildx (`COMPOSE_BAKE=true`), or read the resolved
configuration directly; other providers ignore the optional `x-bake` local-output hint:

```sh
docker compose --profile lambda config | docker buildx bake -f - --load api ingestion minio
docker compose --profile lambda up --build --wait
```

`ingestion` uses the lean `rel` target and Lambda Runtime Interface Emulator. The image's default handler is
`budge.ingestion.handler.handler`; the API Lambda selects `budge.api.handler.handler`. No development tools or
Git metadata are baked into `rel`. MinIO is built from an immutable upstream source commit: the community edition
is [source-only](https://github.com/minio/minio#source-only-distribution), and historical official image tags are
unavailable. Its first build downloads Go dependencies and compiles the server; subsequent builds reuse that layer.

The current API/AWS adapters are skeletons: this stack verifies health, source reload, and S3 availability;
Secrets Manager seeding and application storage wiring remain milestone 2 work.
MinIO enforces conditional writes but ignores `DeleteObject`'s `If-Match`: the future lease adapter must use the
owner re-check fallback described in design spec §12 for local lease release.
