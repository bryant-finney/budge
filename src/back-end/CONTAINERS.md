# Back-end containers

From the repository root, start the API and persistent MinIO with live source edits:

```sh
bin/compose up --build --wait
curl http://127.0.0.1:8000/api/health
bin/compose run --rm api uv run --frozen pytest
bin/compose down
```

`bin/compose` loads `etc/base.env`, then `.env` when present; shell variables take precedence. Change local
ports, image prefix, architecture, or MinIO development credentials there. Endpoints stay in Compose service
environments, so they cannot redirect host AWS/Pulumi commands. Services bind only to loopback by default.
MinIO's console is at `http://127.0.0.1:9001`; data stays in its named volume after `down`.

The launcher obtains `budge.__version__` through the locked uv project and passes it into both image builds.
Images are `ghcr.io/bryant-finney/dev/budge:<version>` and `ghcr.io/bryant-finney/rel/budge:<version>`.
Release versions such as `1.2.3` are unchanged; development versions replace `+` with `-` in the OCI tag only,
because OCI tags cannot contain `+`. The installed package retains the exact version.

The default `dev` image has source, tests, uv, Git, Node, and development tools. The launcher's
`etc/compose/dev.yaml` overlay mounts the checkout and read-only Git common directory at their real absolute
paths, including linked worktrees, and runs uvicorn with reload. The virtual environment stays at `/opt/budge`.
The base `compose.yaml` also runs without this overlay. `CONTAINER_ENGINE=podman bin/compose …` uses a compatible
Podman Compose provider. No Docker-only runtime attributes are required.

Both builds use standard Compose fields. Docker can delegate to Buildx (`COMPOSE_BAKE=true`), or read the resolved
configuration directly; other providers ignore the optional `x-bake` local-output hint:

```sh
bin/compose --profile lambda config | docker buildx bake -f - --load api ingestion minio
bin/compose --profile lambda up --build --wait
curl -X POST http://127.0.0.1:9002/2015-03-31/functions/function/invocations -d '{}'
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
