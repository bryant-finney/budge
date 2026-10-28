// Unit tests for the ingestion Lambda's log format, log group, and failed-connections alarm (#28),
// run in-process against Pulumi mocks.
//
// ref: https://www.pulumi.com/docs/iac/guides/testing/unit/
//
// pattern: install mocks before each test, then drain the runtime with disconnect() so every
// resource registration has landed before asserting on `registered`
import * as pulumi from '@pulumi/pulumi';
import { beforeEach, describe, expect, it } from 'vitest';

import {
  FAILED_CONNECTIONS_METRIC,
  FAILED_CONNECTIONS_PATTERN,
  IngestionObservability,
  LOG_RETENTION_DAYS,
} from '../ingestion.js';

const FUNCTION_NAME = 'budge-ingestion';
const TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:budge-alarms';

const registered: pulumi.runtime.MockResourceArgs[] = [];

/** Resolve an `Output` to its value. Only valid under mocks, where every value is known. */
function promiseOf<T>(output: pulumi.Output<T>): Promise<T> {
  return new Promise((resolve) => {
    output.apply((value) => {
      resolve(value);
      return value;
    });
  });
}

/** Create the component, then wait until every resource registration has reached the mocks. */
async function build(): Promise<IngestionObservability> {
  const component = new IngestionObservability('ingestion', {
    functionName: FUNCTION_NAME,
    alarmTopicArn: TOPIC_ARN,
  });
  await pulumi.runtime.disconnect();
  return component;
}

/** The inputs of the one registered resource of `type`. */
function inputsOf(type: string): Record<string, unknown> {
  const matches = registered.filter((resource) => resource.type === type);
  expect(matches, type).toHaveLength(1);
  const [match] = matches;
  if (match === undefined) throw new Error(`no ${type} registered`);
  return match.inputs as Record<string, unknown>;
}

beforeEach(async () => {
  registered.length = 0;
  await pulumi.runtime.setMocks(
    {
      newResource: (args) => {
        registered.push(args);
        // echo the inputs back as state, so outputs such as LogGroup.name resolve
        const inputs = args.inputs as Record<string, unknown>;
        return { id: `${args.name}-id`, state: { ...inputs, arn: `arn:mock:${args.name}` } };
      },
      call: () => ({}),
    },
    'budge',
    'test',
  );
});

describe('IngestionObservability', () => {
  it('gives the Lambda a JSON log format at INFO, writing to its log group', async () => {
    const component = await build();

    expect(await promiseOf(component.loggingConfig)).toEqual({
      logFormat: 'JSON',
      applicationLogLevel: 'INFO',
      logGroup: `/aws/lambda/${FUNCTION_NAME}`,
    });
  });

  it('keeps the logs for 30 days', async () => {
    await build();

    expect(inputsOf('aws:cloudwatch/logGroup:LogGroup')).toMatchObject({
      name: `/aws/lambda/${FUNCTION_NAME}`,
      retentionInDays: 30,
    });
    expect(LOG_RETENTION_DAYS).toBe(30);
  });

  it('counts failed connections with a metric filter on the run summary', async () => {
    await build();

    const filter = inputsOf('aws:cloudwatch/logMetricFilter:LogMetricFilter');
    expect(FAILED_CONNECTIONS_PATTERN).toBe('{ $.failed_connections > 0 }');
    expect(filter).toMatchObject({
      logGroupName: `/aws/lambda/${FUNCTION_NAME}`,
      pattern: '{ $.failed_connections > 0 }',
      metricTransformation: {
        namespace: FAILED_CONNECTIONS_METRIC.namespace,
        name: FAILED_CONNECTIONS_METRIC.name,
        value: '$.failed_connections',
      },
    });
  });

  it('alarms to the SNS topic when any connection failed', async () => {
    await build();

    expect(inputsOf('aws:cloudwatch/metricAlarm:MetricAlarm')).toMatchObject({
      namespace: FAILED_CONNECTIONS_METRIC.namespace,
      metricName: FAILED_CONNECTIONS_METRIC.name,
      comparisonOperator: 'GreaterThanThreshold',
      threshold: 0,
      treatMissingData: 'notBreaching',
      alarmActions: [TOPIC_ARN],
    });
  });

  it('creates only its log group, metric filter and alarm', async () => {
    await build();

    expect(registered.map((resource) => resource.type).sort()).toEqual([
      'aws:cloudwatch/logGroup:LogGroup',
      'aws:cloudwatch/logMetricFilter:LogMetricFilter',
      'aws:cloudwatch/metricAlarm:MetricAlarm',
      'budge:ingestion:IngestionObservability',
    ]);
  });
});
