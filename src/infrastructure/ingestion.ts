// Observability for the ingestion Lambda (spec §9 run summary, §12 Observability): its log group,
// the JSON log format that keeps the run summary's `extra` fields, and the failed-connections
// alarm. The Lambda itself lands in milestone 4 and takes `loggingConfig` from this component.
//
// ref: https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
// ref: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
//
// pattern: one ComponentResource per cohesive group, children parented to it
import * as aws from '@pulumi/aws';
import * as pulumi from '@pulumi/pulumi';

/** Days the ingestion logs are kept (spec §12). */
export const LOG_RETENTION_DAYS = 30;

/**
 * Matches the handler's run-summary record when any connection's `outcome` is `error` or
 * `login_required`. The handler counts those into the top-level `failed_connections` field.
 */
export const FAILED_CONNECTIONS_PATTERN = '{ $.failed_connections > 0 }';

/** Where the metric filter publishes the failed-connection count. */
export const FAILED_CONNECTIONS_METRIC = {
  namespace: 'budge/Ingestion',
  name: 'FailedConnections',
};

export interface IngestionObservabilityArgs {
  /** The ingestion Lambda's function name; its log group is `/aws/lambda/<name>`. */
  functionName: pulumi.Input<string>;
  /** The SNS topic the spec §12 alarms notify. */
  alarmTopicArn: pulumi.Input<string>;
}

export class IngestionObservability extends pulumi.ComponentResource {
  public readonly logGroup: aws.cloudwatch.LogGroup;
  public readonly failedConnectionsFilter: aws.cloudwatch.LogMetricFilter;
  public readonly failedConnectionsAlarm: aws.cloudwatch.MetricAlarm;
  /**
   * The ingestion Lambda's `loggingConfig`. JSON is required: the text format writes only the
   * message, so the summary's `extra` fields (`summary`, `failed_connections`) never reach
   * CloudWatch, and the metric filter has nothing to match. AWS recommends setting the level
   * here rather than only in code.
   */
  public readonly loggingConfig: pulumi.Output<aws.types.input.lambda.FunctionLoggingConfig>;

  constructor(
    name: string,
    args: IngestionObservabilityArgs,
    opts?: pulumi.ComponentResourceOptions,
  ) {
    super('budge:ingestion:IngestionObservability', name, {}, opts);
    const parent = { parent: this };

    this.logGroup = new aws.cloudwatch.LogGroup(
      `${name}-logs`,
      {
        name: pulumi.interpolate`/aws/lambda/${args.functionName}`,
        retentionInDays: LOG_RETENTION_DAYS,
      },
      parent,
    );

    this.failedConnectionsFilter = new aws.cloudwatch.LogMetricFilter(
      `${name}-failed-connections`,
      {
        logGroupName: this.logGroup.name,
        pattern: FAILED_CONNECTIONS_PATTERN,
        metricTransformation: {
          namespace: FAILED_CONNECTIONS_METRIC.namespace,
          name: FAILED_CONNECTIONS_METRIC.name,
          // the count itself, so the alarm's datapoint says how many connections failed
          value: '$.failed_connections',
          unit: 'Count',
        },
      },
      parent,
    );

    this.failedConnectionsAlarm = new aws.cloudwatch.MetricAlarm(
      `${name}-failed-connections`,
      {
        alarmDescription:
          'An ingestion run had connections with outcome error or login_required (spec §9, §12)',
        namespace: FAILED_CONNECTIONS_METRIC.namespace,
        metricName: FAILED_CONNECTIONS_METRIC.name,
        statistic: 'Maximum',
        comparisonOperator: 'GreaterThanThreshold',
        threshold: 0,
        period: 300,
        evaluationPeriods: 1,
        // the filter publishes only when a run has failures; no data between runs is healthy
        treatMissingData: 'notBreaching',
        alarmActions: [args.alarmTopicArn],
      },
      parent,
    );

    this.loggingConfig = pulumi.output({
      logFormat: 'JSON',
      applicationLogLevel: 'INFO',
      logGroup: this.logGroup.name,
    });

    this.registerOutputs({
      logGroupName: this.logGroup.name,
      failedConnectionsAlarmArn: this.failedConnectionsAlarm.arn,
      loggingConfig: this.loggingConfig,
    });
  }
}
