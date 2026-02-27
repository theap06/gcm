# GPU Clock Policy Compliance - Implementation Guide

This document explains what to implement for the GPU application clock policy compliance and drift detection feature.

## Goal

Detect drift between expected and observed GPU application clocks, classify severity, and expose the result through a health check.

## Where code should live

- Schema and pure policy logic:
  - gcm/schemas/gpu/application_clock.py
  - gcm/schemas/gpu/application_clock_policy.py
- Runtime health check command:
  - gcm/health_checks/checks/check_gpu_clock_policy.py
- Registration/wiring:
  - gcm/health_checks/checks/__init__.py
  - gcm/health_checks/cli/health_checks.py
  - gcm/schemas/health_check/health_check_name.py
- Tests:
  - gcm/tests/schemas/test_application_clock_policy.py
  - gcm/tests/health_checks_tests/test_gpu_clock_policy.py

## What to implement

### 1) Schema + policy logic (pure functions)

In gcm/schemas/gpu/application_clock_policy.py:

- Add `ClockComplianceSeverity` enum: `OK`, `WARN`, `CRITICAL`.
- Add `ClockPolicy` model with:
  - expected graphics frequency (MHz)
  - expected memory frequency (MHz)
  - warn drift threshold (MHz)
  - critical drift threshold (MHz)
- Add `ClockComplianceResult` model with:
  - observed values
  - per-field deltas
  - final severity
- Add evaluator function (for example `evaluate_clock_policy()`) that:
  - computes absolute deltas
  - maps max delta to severity
  - validates threshold consistency (critical >= warn)

### 2) Health check command

In gcm/health_checks/checks/check_gpu_clock_policy.py:

- Create a new click command (`check-gpu-clock-policy`).
- Add options:
  - `--expected-graphics-freq`
  - `--expected-memory-freq`
  - `--warn-delta-mhz`
  - `--critical-delta-mhz`
- Read per-GPU clock telemetry from NVML via existing telemetry client APIs.
- Evaluate policy for each GPU.
- Aggregate to a single exit code:
  - any critical -> `CRITICAL`
  - else any warn -> `WARN`
  - else -> `OK`
- Emit clear messages including expected, observed, and deltas.

### 3) Wiring

- Export command in gcm/health_checks/checks/__init__.py.
- Add command to health check CLI in gcm/health_checks/cli/health_checks.py.
- Add a health check name constant in gcm/schemas/health_check/health_check_name.py.

### 4) Tests

In gcm/tests/schemas/test_application_clock_policy.py:

- exact-match -> `OK`
- warn-threshold breach -> `WARN`
- critical-threshold breach -> `CRITICAL`
- invalid thresholds -> raises error

In gcm/tests/health_checks_tests/test_gpu_clock_policy.py:

- command returns `OK` with compliant data
- command returns `WARN` with moderate drift
- command returns `CRITICAL` with large drift
- multi-GPU worst-case aggregation
- zero-GPU behavior (document and test expected result)

## Recommended implementation order

1. Implement policy models/evaluator + schema tests.
2. Implement command behavior + health check tests.
3. Wire command into CLI and health check name enum.
4. Add/refresh user-facing docs in gcm/health_checks/README.md.

## Definition of done

- New command is visible under `health_checks --help`.
- Unit tests and health check tests pass.
- Command emits deterministic severity and exit code.
- Docs include one example invocation and option meanings.
