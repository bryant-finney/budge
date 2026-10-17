// Runs the Pulumi program in-process against mocks: no Pulumi CLI, no engine, no AWS credentials.
//
// ref: https://www.pulumi.com/docs/iac/guides/testing/unit/
//
// pattern: install mocks before the first program import; import the program fresh per test
import * as pulumi from '@pulumi/pulumi';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

// Type-only (erased): the program itself must be imported dynamically, after setMocks.
import type * as Program from '../index.js';

const registered: pulumi.runtime.MockResourceArgs[] = [];

const BASE_CONFIG = { 'budge:household_timezone': 'America/Chicago' } as const;

/** Resolve an `Output` to its value. Only valid under mocks, where every value is known. */
function promiseOf<T>(output: pulumi.Output<T>): Promise<T> {
  return new Promise((resolve) => {
    output.apply((value) => {
      resolve(value);
      return value;
    });
  });
}

/** Import the program fresh, so it re-reads whatever config the test just set. */
async function runProgram(config: Record<string, string>): Promise<typeof Program> {
  pulumi.runtime.setAllConfig(config);
  vi.resetModules();
  return import('../index.js');
}

beforeAll(async () => {
  // Mocks must be installed before the program module is first imported.
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

beforeEach(() => {
  registered.length = 0;
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
    expect(await promiseOf(program.householdTimezone)).toBe('America/Chicago');
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

  it('rejects a household_timezone that is not an IANA zone', async () => {
    await expect(runProgram({ 'budge:household_timezone': 'Central Time' })).rejects.toThrow(
      /budge:household_timezone must be an IANA time zone/,
    );
  });
});
