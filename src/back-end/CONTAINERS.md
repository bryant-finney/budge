# Back-end containers

Run these builds from the repository root. Both targets use the same pinned Lambda Python base and `uv.lock`.

```sh
docker buildx build --platform linux/arm64 --load -t budge-backend:rel src/back-end
docker buildx build --platform linux/arm64 --target dev --load -t budge-backend:dev src/back-end
```

`rel` is the default target. Its builder syncs runtime dependencies from the frozen lockfile, builds a wheel with
`uv build`, and installs that wheel with `--no-deps`. Only the installed packages and their metadata reach the final
Lambda image. It contains no source checkout, tests, Git metadata, uv, or development dependencies. Builds use the
configured `0.0.0` version fallback because the build context has no Git metadata.

Both Lambdas deploy `rel`. Its default command is `budge.ingestion.handler.handler`; the API Lambda overrides it
with `budge.api.handler.handler`. Outside Lambda, the inherited entrypoint runs the Runtime Interface Emulator on
port 8080:

```sh
docker run --rm -p 9000:8080 budge-backend:rel
docker run --rm -p 9001:8080 budge-backend:rel budge.api.handler.handler
```

`dev` includes editable source, tests, uv, git, Node 24 for pyright, and every development dependency, including
uvicorn and the lint, format, type-check, and test tools. It starts a shell in `/workspace/src/back-end`:

```sh
docker run --rm -it budge-backend:dev
# Inside the container:
uv run --frozen pytest
uv run --frozen ruff check .
```

For live source and the actual Git repository, mount the checkout instead of baking host Git configuration or
credentials into an image. Mount Git's common directory at its existing absolute path too, so linked worktrees
keep working. The environment remains outside the mounted checkout:

```sh
repo="$(git rev-parse --show-toplevel)"
git_common="$(git rev-parse --path-format=absolute --git-common-dir)"
docker run --rm -it \
  --mount "type=bind,source=${repo},target=${repo}" \
  --mount "type=bind,source=${git_common},target=${git_common}" \
  --workdir "${repo}/src/back-end" \
  budge-backend:dev
```

Pass application secrets and service endpoint overrides at container runtime. No `.env` files or AWS endpoint
overrides are included in either image.
