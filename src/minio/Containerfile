# syntax=docker/dockerfile:1

FROM golang:1.24.8-alpine3.22@sha256:3d78beb141d98f42337f1252ecf2a5f20374109929a4c3f6817f9e4179cc0ae5 AS build

# MinIO community releases are source-only. This is RELEASE.2025-10-15T17-29-55Z.
ARG MINIO_COMMIT=9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
RUN CGO_ENABLED=0 go install -trimpath -ldflags='-s -w' github.com/minio/minio@${MINIO_COMMIT}

FROM alpine:3.23.2@sha256:865b95f46d98cf867a156fe4a135ad3fe50d2056aa3f25ed31662dff6da4eb62

ARG MINIO_COMMIT=9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
    org.opencontainers.image.revision="${MINIO_COMMIT}"
COPY --from=build /go/bin/minio /usr/local/bin/minio
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /go/pkg/mod/github.com/minio/minio@*/LICENSE /licenses/minio/LICENSE
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
