---
name: lambda-logging-format
description: How Lambda's Python runtime captures stdlib logging (text prefix vs JSON `message` string) and why the §12 run-summary metric filter needs JSON format plus top-level `extra` fields
metadata:
  type: reference
---

# Lambda Python logging and the §12 metric filter

Source: <https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html> (checked 2026-10-18).

- **Text format (the default):** each record is `[INFO]\t<ts>\t<requestId>\t<message>`, and the runtime's default
  level is WARN, so `logger.setLevel(INFO)` in code is needed for INFO lines.
- **JSON format (advanced logging controls, `LoggingConfig.LogFormat = JSON`):** each record is
  `{timestamp, level, message, logger, requestId}`, and keys passed in `extra={...}` become top-level fields. A JSON
  string logged as the message stays a string, so a filter can't look inside it. AWS recommends
  `ApplicationLogLevel` over `setLevel` in code. `print` output stays plain text.
- **Consequence for budge:** #26's stub logs the run summary as `logger.info('%s', json.dumps(summary))`. Neither
  format lets §12's metric filter count `outcome` ∈ {error, login_required}, and the summary's keys are connection
  ids anyway. The proposal raised on PR #26 is `extra={'summary': ..., 'failed_connections': n}` plus JSON log format
  (infra), with the filter on `$.failed_connections`. Decide it when `run_ingestion` lands in M2.

Related: [[pydantic-model-notes]].
