# GPU Application Clock Policy Compliance: Implementation Guide

This folder is a starter implementation guide for adding GPU application clock policy compliance and drift detection.

## Local repository path

Your local repository root is:

/Users/achintyapaningapalli/gcm

The guide below uses workspace-relative paths.

## What is already added

- Policy schema and evaluation helpers:
  - [gcm/schemas/gpu/application_clock_policy.py](gcm/schemas/gpu/application_clock_policy.py)
- New health check command template:
  - [gcm/health_checks/checks/check_gpu_clock_policy.py](gcm/health_checks/checks/check_gpu_clock_policy.py)
- CLI registration points:
  - [gcm/health_checks/checks/__init__.py](gcm/health_checks/checks/__init__.py)
  - [gcm/health_checks/cli/health_checks.py](gcm/health_checks/cli/health_checks.py)
- Health check naming enum:
  - [gcm/schemas/health_check/health_check_name.py](gcm/schemas/health_check/health_check_name.py)
- Starter tests:
  - [gcm/tests/health_checks_tests/test_gpu_clock_policy.py](gcm/tests/health_checks_tests/test_gpu_clock_policy.py)

## What this feature should do

Given an expected policy:

- expected graphics application clock (MHz)
- expected memory application clock (MHz)
- warn drift threshold (MHz)
- critical drift threshold (MHz)

the check should:

1. read observed GPU clocks from NVML,
2. calculate drift per GPU,
3. classify each GPU as `ok`, `warn`, or `critical`,
4. return overall exit code (`OK`, `WARN`, `CRITICAL`) based on worst GPU,
5. publish telemetry output that includes expected, observed, and deltas.

## Files you should reference while implementing

### Core feature files

- [gcm/schemas/gpu/application_clock_policy.py](gcm/schemas/gpu/application_clock_policy.py)
- [gcm/health_checks/checks/check_gpu_clock_policy.py](gcm/health_checks/checks/check_gpu_clock_policy.py)
- [gcm/tests/health_checks_tests/test_gpu_clock_policy.py](gcm/tests/health_checks_tests/test_gpu_clock_policy.py)

### Existing NVIDIA check patterns (copy conventions from here)

- [gcm/health_checks/checks/check_nvidia_smi.py](gcm/health_checks/checks/check_nvidia_smi.py)
- [gcm/tests/health_checks_tests/test_nvidia_smi.py](gcm/tests/health_checks_tests/test_nvidia_smi.py)

### Shared CLI / telemetry plumbing

- [gcm/health_checks/click.py](gcm/health_checks/click.py)
- [gcm/health_checks/check_utils/telem.py](gcm/health_checks/check_utils/telem.py)
- [gcm/health_checks/check_utils/output_context_manager.py](gcm/health_checks/check_utils/output_context_manager.py)

### Device telemetry interface

- [gcm/monitoring/device_telemetry_client.py](gcm/monitoring/device_telemetry_client.py)
- [gcm/monitoring/device_telemetry_nvml.py](gcm/monitoring/device_telemetry_nvml.py)
- [gcm/schemas/gpu/application_clock.py](gcm/schemas/gpu/application_clock.py)

### Registration and command surfacing

- [gcm/health_checks/checks/__init__.py](gcm/health_checks/checks/__init__.py)
- [gcm/health_checks/cli/health_checks.py](gcm/health_checks/cli/health_checks.py)
- [gcm/schemas/health_check/health_check_name.py](gcm/schemas/health_check/health_check_name.py)

### Docs and config examples

- [gcm/health_checks/README.md](gcm/health_checks/README.md)
- [templates/gpu_clock_policy_compliance/config-template.toml](templates/gpu_clock_policy_compliance/config-template.toml)

## Step-by-step implementation plan

### Step 1: finalize policy semantics

In [gcm/schemas/gpu/application_clock_policy.py](gcm/schemas/gpu/application_clock_policy.py):

- confirm threshold semantics (`>` vs `>=`),
- ensure invalid threshold combinations raise clear errors,
- keep this module pure and testable.

### Step 2: finish command behavior

In [gcm/health_checks/checks/check_gpu_clock_policy.py](gcm/health_checks/checks/check_gpu_clock_policy.py):

- validate CLI values (non-negative thresholds),
- improve per-GPU output formatting,
- decide behavior for `device_count == 0` (warn vs critical based on your policy),
- ensure overall exit code is the worst severity across GPUs.

### Step 3: config support

- Start by documenting expected keys in
  [templates/gpu_clock_policy_compliance/config-template.toml](templates/gpu_clock_policy_compliance/config-template.toml).
- Then wire command defaults to config resolution patterns used by other checks.
- Add one explicit test that config values override defaults.

### Step 4: tests

Add or extend tests in [gcm/tests/health_checks_tests/test_gpu_clock_policy.py](gcm/tests/health_checks_tests/test_gpu_clock_policy.py):

- `OK` path (no drift),
- `WARN` path (drift above warn threshold only),
- `CRITICAL` path,
- invalid threshold input,
- zero-GPU behavior,
- mixed GPU outcomes where overall result should be worst severity.

### Step 5: docs

Update [gcm/health_checks/README.md](gcm/health_checks/README.md) with:

- command description,
- options and examples,
- interpretation of output fields,
- operational guidance on threshold tuning.

## Example command

```shell
health_checks check-gpu-clock-policy fair_cluster prolog \
  --expected-graphics-freq 1155 \
  --expected-memory-freq 1593 \
  --warn-delta-mhz 30 \
  --critical-delta-mhz 75 \
  --sink=stdout
```

## Recommended PR split

1. Schema + evaluation logic + unit tests.
2. Health check command behavior + command tests.
3. Config defaults + docs + rollout notes.

Use checklist: [templates/gpu_clock_policy_compliance/PR-CHECKLIST.md](templates/gpu_clock_policy_compliance/PR-CHECKLIST.md)

