// Pulumi program entrypoint: load the stack config, declare its resources, export its outputs.
// Milestone 1 creates no resources: it only loads and validates config and exports non-secret
// settings as stack outputs. AWS resources land in milestone 4.
//
// ref: https://www.pulumi.com/docs/iac/languages-sdks/javascript/
//
// pattern: one ComponentResource per cohesive group (static site, API, ingestion), each in its
// own module beside this file (flat layout, no nested src/)
import * as pulumi from '@pulumi/pulumi';

import { loadConfig } from './src/config';

const config = loadConfig();

export const plaidEnv = pulumi.output(config.plaidEnv);
export const scheduleRate = pulumi.output(config.scheduleRate);
export const householdTimezone = pulumi.output(config.householdTimezone);
