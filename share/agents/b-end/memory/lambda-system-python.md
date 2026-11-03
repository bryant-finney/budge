---
name: lambda-system-python
description: budge images install into the Lambda base image's system Python, which ships awslambdaric, boto3 and more outside uv.lock; plain uv sync removes them, and rel uses an editable install to keep one copy of the code
metadata:
  type: project
---

# Installing into the Lambda system Python

The images install into `/var/lang` with `UV_PROJECT_ENVIRONMENT=/var/lang`, at the owner's request (PR #34), with no
virtual environment.

- A plain `uv sync` there uninstalled 11 packages in a test on 2026-11-03: `awslambdaric` (which the runtime's
  `bootstrap.py` imports), `boto3`, `botocore`, `jmespath`, `python-dateutil`, `s3transfer`, `simplejson`, `six`,
  `snapshot-restore-py`, `urllib3` and `budge`. Always pass `--inexact`. There's no `EXTERNALLY-MANAGED` marker to stop it.
- `rel` copies `budge/` to `/var/task` and only the `*budge*` entries of site-packages from the build stage. A regular
  wheel beside that source would give two copies, with `/var/task` winning the import and having no `_version.py`.
  The editable install gives one copy, and its metadata is in site-packages. `UV_COMPILE_BYTECODE` skips editable
  source, so the build runs `compileall`.
- `rel` is `FROM dependencies`, so that stage's uv settings are `ARG`, not `ENV`. Otherwise they'd show up in the image
  config. `FROM base` plus a copy of site-packages would duplicate the base's 50 MB.
- A stage built `FROM` another inherits its `ARG`s, so only `dependencies` declares them, by the owner's choice. BuildKit
  and Podman 5.8.9 (Buildah 1.43.5) gave the same values in a child stage's `RUN` on 2026-11-03. Read `docker history`
  for what a `RUN` really gets. `ARG`s stay out of `Config.Env`, so `rel` is still clean.
- To test Podman without installing it: `docker run --rm --privileged -v /var/lib/containers -v <writable clone>:/ctx quay.io/podman/stable podman --storage-driver vfs build ...`. With overlay storage, every `RUN` fails on exec with
  `invalid argument`. A read-only context fails on file bind mounts with `read-only file system`. Neither is a problem
  with the Containerfile. That image has no Compose provider, so it can't test `extends.file`.
- `.dockerignore` keeps the host's `budge/_version.py` out, so a stale one can't reach an image.
- See [[dev-image-no-uv-or-git]] for the `dev` side.
