---
name: pulumi-mock-test-harness
description: Pulumi setMocks unit tests see an empty resource registry unless the RPC queue is drained; fix with beforeEach(setMocks) plus runtime.disconnect(); Pulumi's runtime loads the CJS entrypoint via vendored ts-node 7
metadata:
  type: project
---

# Pulumi mock test harness (`src/infrastructure/tests/`)

Found while reviewing PR #21 (#13), 2026-10-17. The fix is applied in `tests/program.test.ts`.

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
- **Applied in #21 (`d3a4c91`, 2026-10-18).** With a `CustomResource` and a `ComponentResource`
  injected into `index.ts`, the old harness passed 6/6, and the drained one failed
  `creates no resources` with both resources listed. On the unmodified program, it passed 6/6.
- **The runtime loads the CommonJS entrypoint.** `@pulumi/pulumi@3.269.0` `cmd/run/run.js`, outside
  ESM mode, uses the project's TypeScript (pnpm links the optional peer, giving
  `@pulumi+pulumi@3.269.0_typescript@6.0.3`) with the vendored `ts-node@7.0.1`. An emulation of that
  registration loaded `index.ts` and type-checked it: `noCheck` is unset, so `transpileOnly` is
  undefined, and an injected TS2322 was rejected. The real smoke test passed on 2026-10-18 (Pulumi
  v3.270.0, #21 `d3a4c91`): 1 stack resource plus the 3 outputs. It passed again on 2026-10-20 at
  `e2d854e`, after the round-3 `config.ts` changes. Rerun it whenever `config.ts` or `index.ts`
  changes, because the unit tests don't load the program through Pulumi's runtime.
- **Smoke-test safety:** agent shells already export `PULUMI_BACKEND_URL=s3://budge-pulumi-state-…`
  and `AWS_PROFILE=budge` (from `.env`). For a throwaway stack, override all of these inline:
  `PULUMI_BACKEND_URL=file://<worktree>/.cache/smoke/state`, `PULUMI_HOME=<worktree>/.cache/smoke/home`
  (keeps `~/.pulumi` untouched) and `PULUMI_CONFIG_PASSPHRASE=…`, plus `unset AWS_PROFILE`. Then run
  `pulumi stack init smoke --non-interactive`, `pulumi config set household_timezone …` and
  `pulumi preview`. Clean up with `pulumi stack rm smoke --yes`, then delete the `.cache/smoke` dir
  and `Pulumi.smoke.yaml`.
  `setAllConfig` replaces the whole config (it doesn't merge), so a missing-key test really runs
  without the key.

**Why:** a test that can't fail let #21's "creates no resources" check pass without testing
anything. Milestone 4's resource-input assertions use the same harness.
**How to apply:** every `setMocks` test that inspects registered resources or their inputs must
drain with `disconnect()` first. When adding such a test, inject a resource once to prove it fails.
See also [[pnpm-node-tooling-gotchas]].
