---
name: pulumi-mock-test-harness
description: Pulumi setMocks unit tests see an empty resource registry unless the RPC queue is drained; fix with beforeEach(setMocks) plus runtime.disconnect(); Pulumi's runtime loads the CJS entrypoint via vendored ts-node 7
metadata:
  type: project
---

# Pulumi mock test harness (`src/infrastructure/tests/`)

Found while reviewing PR #21 (#13), 2026-10-17.

- **Resource assertions race the mocks.** Resource registration is async. The mock's
  `newResource` runs only after the `register*` promise chain settles, which happens after
  `await import('../index.js')` resolves. A check on the collected `registered` array right after the
  import therefore sees `[]` whatever the program creates. #21's "creates no resources" test passed
  with a `CustomResource` and a `ComponentResource` injected into `index.ts`.
- **Fix:** install the mocks in `beforeEach(async () => { await pulumi.runtime.setMocks(...) })`,
  not `beforeAll`, and drain inside the import helper:
  `const program = await import('../index.js'); await pulumi.runtime.disconnect(); return program;`.
  `disconnect()` waits for the RPC queue (`rpcDone`) to drain and then closes the connection, so the
  mocks must be installed again for each test. A bare `setImmediate` tick also exposed the
  resources, but only by timing, so don't rely on it.
- **How it was verified** (in a scratch copy of the #21 tip): with the probe resources injected, the
  drained test saw both resources and failed. A later test that registered resources after an
  earlier `disconnect()` still passed. On the unmodified program, all tests passed.
- **The runtime loads the CommonJS entrypoint.** `@pulumi/pulumi@3.269.0` `cmd/run/run.js`, outside
  ESM mode, uses the project's TypeScript (pnpm links the optional peer, giving
  `@pulumi+pulumi@3.269.0_typescript@6.0.3`) with the vendored `ts-node@7.0.1`. An emulation of that
  registration loaded `index.ts` and type-checked it: `noCheck` is unset, so `transpileOnly` is
  undefined, and an injected TS2322 was rejected. This is an emulation, not `pulumi preview`.
  `setAllConfig` replaces the whole config (it doesn't merge), so a missing-key test really runs
  without the key.

**Why:** a test that can't fail let #21's "creates no resources" check pass without testing
anything. Milestone 4's resource-input assertions use the same harness.
**How to apply:** every `setMocks` test that inspects registered resources or their inputs must
drain with `disconnect()` first. When adding such a test, inject a resource once to prove it fails.
See also [[pnpm-node-tooling-gotchas]].
