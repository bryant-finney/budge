# syntax=docker/dockerfile:1

# The back end's one container image (spec §12 Compute): both Lambdas deploy from it with different handlers, and
# `docker compose` (milestone 2) runs it locally. Build it for Graviton from the repo root:
#
#   docker buildx build --platform linux/arm64 --load -t budge-backend:dev src/back-end
#
# - Default command: the ingestion handler, `budge.ingestion.handler.handler` (the compose `ingestion` service and the
#   ingestion Lambda use it as is).
# - The API Lambda overrides it with `budge.api.handler.handler` (Pulumi `imageConfig.commands`).
# - Outside Lambda, the base image's entrypoint starts the bundled Runtime Interface Emulator on port 8080.
#
# No secrets, `.env` files or AWS endpoint overrides belong in the image (spec §12): they come from the environment.

# uv, for the dependency install only: it is bind-mounted into that `RUN`, so it never ships in the image. The version
# satisfies `[tool.uv] required-version` in pyproject.toml; bump the tag and digest together.
FROM ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff AS uv

# The newest generally available Lambda Python runtime (`python3.15` is Lambda preview-only), pinned by tag and by the
# multi-platform index digest, so `--platform` still selects the `linux/arm64` image. Bump both together.
FROM public.ecr.aws/lambda/python:3.14@sha256:fc4e15a5e09e2c9b6184810ea0fdc87afe1c1c734c98cbe27d739a35c3f15e7e AS base

# The runtime dependencies alone, installed into the task root from `uv.lock`. The layer depends only on
# `pyproject.toml` and `uv.lock`, so a code change doesn't reinstall them.
FROM base AS dependencies

# compile bytecode now: the task root is read-only on Lambda, so it can't cache `.pyc` files at cold start. `copy`
# because the uv cache is a mount; no installer metadata, so the layer is reproducible; and never download a Python:
# the image's own interpreter is the runtime
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_INSTALLER_METADATA=1 \
    UV_PYTHON_DOWNLOADS=never

# `--frozen`: resolve from `uv.lock` alone, never re-lock; `--no-dev`: runtime dependencies only (no pytest, mypy, ruff
# or pyright); `--no-emit-project`: the `budge` package itself is copied in below, not installed
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=/tmp/budge/pyproject.toml \
    --mount=type=bind,source=uv.lock,target=/tmp/budge/uv.lock \
    uv export --project /tmp/budge --frozen --no-dev --no-emit-project --no-header --format requirements-txt \
        --output-file /tmp/requirements.txt \
    && uv pip install --python /var/lang/bin/python3 --target "${LAMBDA_TASK_ROOT}" \
        --requirements /tmp/requirements.txt \
    && rm /tmp/requirements.txt

FROM base

COPY --from=dependencies ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# only the package: no tests, dev tools, `.venv` or the build-time `budge/_version.py` (see `.dockerignore`), so
# `budge.__version__` is the `0.0.0` fallback in the image. Compiled for the same read-only reason as the dependencies
COPY budge/ ${LAMBDA_TASK_ROOT}/budge/
RUN python3 -m compileall -q "${LAMBDA_TASK_ROOT}/budge"

CMD ["budge.ingestion.handler.handler"]
