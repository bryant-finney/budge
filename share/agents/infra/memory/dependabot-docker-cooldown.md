---
name: dependabot-docker-cooldown
description: Dependabot's docker cooldown has a publication date only for Docker Hub images; other registries skip it, and git-pinned commits only follow a branch tip
metadata:
  type: reference
---

# Dependabot docker cooldown

`docker/lib/dependabot/docker/update_checker.rb` in `dependabot/dependabot-core` gets a date only
when `using_dockerhub?` (the `tag_last_pushed` field of Hub's tag API). For any other registry it
logs "No verified registry publication date source" and proposes the update with no cooldown.
`file_parser.rb` treats a `docker.io/` prefix as Docker Hub, so fully qualified names keep the
cooldown.

Found on PR #34 (2026-11-02). Before moving an image to a Hub mirror, compare digests with
`docker buildx imagetools inspect`:

- `astral/uv` has the same multi-platform digest as `ghcr.io/astral-sh/uv`.
- `amazon/aws-lambda-python` publishes only single-architecture tags (`3.14-arm64`), with different
  digests from `public.ecr.aws/lambda/python`, so `--platform` overrides can't select from it.

To track a commit outside a `FROM` line, `gitsubmodule` follows only the head of a branch, not
release tags. `gomod` keeps a pseudo-version when the module has no tagged versions.
