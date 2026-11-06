---
name: docker-disk-full-minio
description: MinIO exiting with "drive path full" or "Unable to use the drive /data" means the Docker VM disk is full, not a Compose bug; root containers still write
metadata:
  type: project
---

# Full Docker disk stops MinIO first

On 2026-11-02, `docker compose up --wait` failed with `container minio exited (1)` and logs saying
`drive path full` and `Unable to use the drive /data`. The Compose change under test wasn't the
cause: the Docker Desktop VM disk was at 100% (`docker run --rm alpine df -h /`). The filesystem's
reserved blocks let root keep writing, so a root probe succeeds while MinIO, running as uid 1000,
fails.

**How to apply:** check `df` in a container before debugging a MinIO exit. Don't prune all of Docker
to fix it, because other worktrees' stacks and images share the daemon; remove only the images a run
built, and tell the user how full the disk is. To test `api` and `ingestion` alone, use
`docker compose --profile lambda up --no-build --no-deps -d api ingestion`.
