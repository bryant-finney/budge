---
name: cloudfront-viewer-ip
description: behind CloudFront's AllViewerExceptHostHeader policy, request.client is the edge IP; the viewer IP is in cloudfront-viewer-address
metadata:
  type: reference
---

# The viewer's IP behind CloudFront

- The `/api/*` behavior uses the `AllViewerExceptHostHeader` origin request policy (spec §4). API Gateway's
  `requestContext.http.sourceIp` is the TCP peer, which is the **CloudFront edge** (the last `x-forwarded-for` hop).
  Mangum maps `sourceIp` to the ASGI `client`, so on AWS `request.client.host` is always a CloudFront IP.
- The viewer's address is in the `cloudfront-viewer-address` header (`<ip>:<port>`). Anything that needs the
  viewer IP (logging a rejected sign-in, rate limiting) reads that header, never `request.client`.
- The policy forwards every viewer header except `Host`, so the viewer's own `User-Agent` arrives (`curl/...` for the
  smoke test). It also adds `cloudfront-forwarded-proto`, `cloudfront-viewer-country*` and the other CloudFront
  request headers ([AWS docs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-origin-request-policies.html#managed-origin-request-policy-all-viewer-except-host-header)).
- `tests/events/apigw-v2-get-health.json` models this, and `test_handler_client_is_the_cloudfront_edge` pins it
  (PR #26 review). Replace the fixture with a real capture in M4.

Related: [[mangum-event-loop]].
