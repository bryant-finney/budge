// Runs the Pulumi program in-process against mocks: no Pulumi CLI, no engine, no AWS credentials.
//
// ref: https://www.pulumi.com/docs/iac/guides/testing/unit/
//
// pattern: install mocks before each program import; import the program fresh per test, then
// drain the runtime with disconnect() so every resource registration has landed before asserting
import * as pulumi from '@pulumi/pulumi';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Constants only: config.ts registers no resources, so importing it statically is safe.
import { IANA_ZONES_MISSING_FROM_ICU } from '../config.js';
// Type-only (erased): the program itself must be imported dynamically, after setMocks.
import type * as Program from '../index.js';

const registered: pulumi.runtime.MockResourceArgs[] = [];

const BASE_CONFIG = {
  'aws:region': 'us-east-1',
  'budge:household_timezone': 'America/New_York',
} as const;

/** Resolve an `Output` to its value. Only valid under mocks, where every value is known. */
function promiseOf<T>(output: pulumi.Output<T>): Promise<T> {
  return new Promise((resolve) => {
    output.apply((value) => {
      resolve(value);
      return value;
    });
  });
}

/**
 * Import the program fresh, so it re-reads whatever config the test just set, then drain it.
 *
 * Resource registration is async: the mock's `newResource` runs only after the `import()` has
 * resolved. `disconnect()` waits for every outstanding RPC, so `registered` is complete when this
 * returns. It also closes the mock connection, which is why `beforeEach` installs the mocks again.
 */
async function runProgram(config: Record<string, string>): Promise<typeof Program> {
  pulumi.runtime.setAllConfig(config);
  vi.resetModules();
  const program = await import('../index.js');
  await pulumi.runtime.disconnect();
  return program;
}

beforeEach(async () => {
  registered.length = 0;
  // Mocks must be installed before the program module is imported, and again after each
  // disconnect().
  await pulumi.runtime.setMocks(
    {
      newResource: (args) => {
        registered.push(args);
        return { id: `${args.name}-id`, state: {} };
      },
      call: () => ({}),
    },
    'budge',
    'test',
  );
});

describe('program outputs', () => {
  it('exports the configured settings', async () => {
    const program = await runProgram({
      ...BASE_CONFIG,
      'budge:plaid_env': 'production',
      'budge:schedule_rate': 'rate(1 hour)',
    });

    expect(await promiseOf(program.plaidEnv)).toBe('production');
    expect(await promiseOf(program.scheduleRate)).toBe('rate(1 hour)');
    expect(await promiseOf(program.householdTimezone)).toBe('America/New_York');
  });

  it('defaults plaid_env to sandbox and schedule_rate to every 4 hours', async () => {
    const program = await runProgram({ ...BASE_CONFIG });

    expect(await promiseOf(program.plaidEnv)).toBe('sandbox');
    expect(await promiseOf(program.scheduleRate)).toBe('rate(4 hours)');
  });

  it('creates no resources', async () => {
    await runProgram({ ...BASE_CONFIG });

    expect(registered).toEqual([]);
  });
});

describe('config validation', () => {
  it('rejects an unknown plaid_env', async () => {
    await expect(runProgram({ ...BASE_CONFIG, 'budge:plaid_env': 'development' })).rejects.toThrow(
      /budge:plaid_env must be one of sandbox, production; got "development"/,
    );
  });

  it('fails when household_timezone is missing', async () => {
    await expect(runProgram({})).rejects.toThrow(/household_timezone/);
  });

  it.each(['Central Time', 'america/chicago', '+05:30', 'US/Central'])(
    'rejects household_timezone %j, which is not an exact IANA zone name',
    async (zone) => {
      await expect(runProgram({ 'budge:household_timezone': zone })).rejects.toThrow(
        /budge:household_timezone must be an IANA time zone/,
      );
    },
  );

  it.each(['America/Chicago', 'Asia/Calcutta', 'Asia/Kolkata', 'Europe/Kyiv', 'UTC'])(
    'accepts household_timezone %j, current or linked IANA name, unchanged',
    async (zone) => {
      const program = await runProgram({ ...BASE_CONFIG, 'budge:household_timezone': zone });

      expect(await promiseOf(program.householdTimezone)).toBe(zone);
    },
  );

  it('supplements Intl.supportedValuesOf only with zones the runtime accepts', () => {
    const icu = new Set(Intl.supportedValuesOf('timeZone'));

    for (const zone of IANA_ZONES_MISSING_FROM_ICU) {
      expect(() => new Intl.DateTimeFormat('en-US', { timeZone: zone }), zone).not.toThrow();
      expect(icu.has(zone), `${zone} is already in supportedValuesOf`).toBe(false);
    }
  });

  it.each(['rate(1 hours)', 'rate(15 minutes)', 'rate(2 days)', 'cron(0 */4 * * ? *)'])(
    'accepts schedule_rate %j',
    async (rate) => {
      const program = await runProgram({ ...BASE_CONFIG, 'budge:schedule_rate': rate });

      expect(await promiseOf(program.scheduleRate)).toBe(rate);
    },
  );

  it.each([
    'rate(4 hour)',
    'rate(4 hours',
    'rate(0 hours)',
    'rate(04 hours)',
    'rate(4 weeks)',
    'cron(0 */4 * * ?)',
    'at(2026-11-20T13:00:00)',
  ])('rejects schedule_rate %j', async (rate) => {
    await expect(runProgram({ ...BASE_CONFIG, 'budge:schedule_rate': rate })).rejects.toThrow(
      /Configuration 'budge:schedule_rate' value .* does not match the regular expression/,
    );
  });
});
