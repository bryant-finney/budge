// Typed, validated view of the stack's `budge:*` Pulumi config.
//
// ref: https://www.pulumi.com/docs/iac/concepts/config/
//
// pattern: keys use the spec's snake_case names; secrets are read with getSecret, never get
import * as pulumi from '@pulumi/pulumi';

/** Plaid environments the stack can point at (spec §11). */
export const PLAID_ENVS = ['sandbox', 'production'] as const;
export type PlaidEnv = (typeof PLAID_ENVS)[number];

/** EventBridge Scheduler expression used when `schedule_rate` is unset (spec §12). */
export const DEFAULT_SCHEDULE_RATE = 'rate(4 hours)';

/** Typed, validated view of the `budge:*` Pulumi config the skeleton needs. */
export interface BudgeConfig {
  readonly plaidEnv: PlaidEnv;
  readonly scheduleRate: string;
  readonly householdTimezone: string;
}

function isPlaidEnv(value: string): value is PlaidEnv {
  return (PLAID_ENVS as readonly string[]).includes(value);
}

/**
 * Read and validate the stack's `budge:*` config.
 *
 * Keys use the spec's snake_case names. Throws on an unknown `plaid_env`, a missing
 * `household_timezone`, or a `household_timezone` that is not a canonical IANA zone.
 */
export function loadConfig(config: pulumi.Config = new pulumi.Config('budge')): BudgeConfig {
  const plaidEnv = config.get('plaid_env') ?? 'sandbox';
  if (!isPlaidEnv(plaidEnv)) {
    throw new Error(
      `budge:plaid_env must be one of ${PLAID_ENVS.join(', ')}; got ${JSON.stringify(plaidEnv)}`,
    );
  }

  const householdTimezone = config.require('household_timezone');
  if (!Intl.supportedValuesOf('timeZone').includes(householdTimezone)) {
    throw new Error(
      `budge:household_timezone must be an IANA time zone (e.g. America/Chicago); got ${JSON.stringify(householdTimezone)}`,
    );
  }

  return {
    plaidEnv,
    scheduleRate: config.get('schedule_rate') ?? DEFAULT_SCHEDULE_RATE,
    householdTimezone,
  };
}
