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

/**
 * Recurring EventBridge Scheduler expressions: `rate(<n> <unit>)` or a six-field `cron(...)`.
 *
 * A value of 1 takes the singular or plural unit; a larger value takes the plural, as the
 * Scheduler docs list it. One-time `at(...)` schedules are rejected, because ingestion recurs.
 */
export const SCHEDULE_RATE_PATTERN =
  /^(?:rate\((?:1 (?:minute|hour|day)s?|[1-9]\d* (?:minutes|hours|days))\)|cron\(\S+(?: \S+){5}\))$/;

/**
 * Current IANA zone names that `Intl.supportedValuesOf('timeZone')` leaves out.
 *
 * That list holds ICU/CLDR's canonical IDs, which are often the pre-rename IANA links
 * (`Asia/Calcutta`, not `Asia/Kolkata`), and it omits `UTC` and every `Etc/*` zone. These are the
 * `Z` (zone) lines of tzdata 2026e's `tzdata.zi` minus that list on Node 24.22.0 (ICU 78.3, tz
 * 2026c), less `Factory`, plus the `UTC` link. Matching is exact and case-sensitive, so
 * `america/chicago` and offsets such as `+05:30` stay rejected; the back end's `zoneinfo` accepts
 * every name here. Regenerate after an ICU upgrade or an IANA rename.
 */
export const IANA_ZONES_MISSING_FROM_ICU: ReadonlySet<string> = new Set([
  'America/Argentina/Buenos_Aires',
  'America/Argentina/Catamarca',
  'America/Argentina/Cordoba',
  'America/Argentina/Jujuy',
  'America/Argentina/Mendoza',
  'America/Indiana/Indianapolis',
  'America/Kentucky/Louisville',
  'America/Nuuk',
  'Asia/Ho_Chi_Minh',
  'Asia/Kathmandu',
  'Asia/Kolkata',
  'Asia/Yangon',
  'Atlantic/Faroe',
  'Europe/Kyiv',
  'Pacific/Kanton',
  'CST6CDT',
  'EST5EDT',
  'MST7MDT',
  'PST8PDT',
  'UTC',
  'Etc/UTC',
  'Etc/GMT',
  ...Array.from({ length: 14 }, (_, i) => `Etc/GMT-${String(i + 1)}`),
  ...Array.from({ length: 12 }, (_, i) => `Etc/GMT+${String(i + 1)}`),
]);

/** Typed, validated view of the `budge:*` Pulumi config the skeleton needs. */
export interface BudgeConfig {
  readonly plaidEnv: PlaidEnv;
  readonly scheduleRate: string;
  readonly householdTimezone: string;
}

function isPlaidEnv(value: string): value is PlaidEnv {
  return (PLAID_ENVS as readonly string[]).includes(value);
}

function isIanaTimeZone(zone: string): boolean {
  return IANA_ZONES_MISSING_FROM_ICU.has(zone) || Intl.supportedValuesOf('timeZone').includes(zone);
}

/**
 * Read and validate the stack's `budge:*` config.
 *
 * Keys use the spec's snake_case names. Throws on an unknown `plaid_env`, a `schedule_rate` that
 * is not a recurring Scheduler expression, a missing `household_timezone`, or a
 * `household_timezone` that is not an exact IANA zone name.
 */
export function loadConfig(config: pulumi.Config = new pulumi.Config('budge')): BudgeConfig {
  const plaidEnv = config.get('plaid_env') ?? 'sandbox';
  if (!isPlaidEnv(plaidEnv)) {
    throw new Error(
      `budge:plaid_env must be one of ${PLAID_ENVS.join(', ')}; got ${JSON.stringify(plaidEnv)}`,
    );
  }

  const householdTimezone = config.require('household_timezone');
  if (!isIanaTimeZone(householdTimezone)) {
    throw new Error(
      `budge:household_timezone must be an IANA time zone name, case-sensitive (e.g. America/Chicago); got ${JSON.stringify(householdTimezone)}`,
    );
  }

  return {
    plaidEnv,
    scheduleRate:
      config.get('schedule_rate', { pattern: SCHEDULE_RATE_PATTERN }) ?? DEFAULT_SCHEDULE_RATE,
    householdTimezone,
  };
}
