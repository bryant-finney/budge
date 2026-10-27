---
name: lambda-logging-format
description: How Lambda's Python runtime captures stdlib logging (text prefix vs JSON `message` string), and the run-summary `extra` fields (`summary`, `failed_connections`) §12's metric filter reads
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
- **Consequence for budge (decided on PR #26, 2026-10-25):** a `json.dumps(summary)` message is unreadable by §12's
  metric filter in either format, and the summary's keys are connection ids, so there's no fixed path to `outcome`.
  The handler now logs `logger.info('ingestion run summary', extra={'summary': ..., 'failed_connections': n})`, with
  `n = count_failed(summary)` from `budge.ingestion.summary`. Infra must set `LogFormat: JSON` and
  `ApplicationLogLevel: INFO` on the ingestion function; the filter is `{ $.failed_connections > 0 }`. In text format
  the `extra` fields aren't printed at all, so JSON format is mandatory, not optional. The handler doesn't call
  `logger.setLevel`; `ApplicationLogLevel` alone sets the level, so code and function config can't disagree.
- **Testing `extra`:** `LogRecord` has no typed `summary` attribute, so strict pyright/mypy/ty reject
  `record.summary`; read `vars(record)['summary']` (ruff B009 flags `getattr` with a constant).

Related: [[pydantic-model-notes]].
