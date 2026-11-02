---
name: lambda-rie-overlap-crash
description: The Lambda Runtime Interface Emulator panics and exits with code 2 on overlapping invocations, so don't health-check by invoking on a timer
metadata:
  type: project
---

# The Lambda emulator can't take overlapping invocations

On 2026-11-02, three concurrent `curl` invocations against `public.ecr.aws/lambda/python:3.14` killed
the container: `ReserveFailed: AlreadyReserved`, then a nil pointer panic in
`rapidcore.(*Server).Invoke`, exit code 2. A health probe that invokes the handler every few seconds
can do the same thing to a real request, and the risk grows as the handler gets slower.

The emulator's status codes are also misleading: a handler that raises returns HTTP 200 with
`errorMessage` in the body, and one that can't be imported returns 502.

**How to apply:** for `api` on `rel`, the probe in `etc/compose/targets/rel.yaml` calls the handler
until it passes, then only checks the port. Check `statusCode` in the response body, never only the
HTTP status. Don't send parallel requests to an emulator in a test unless you mean to crash it.
