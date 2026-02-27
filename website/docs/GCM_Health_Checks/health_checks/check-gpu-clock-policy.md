# check-gpu-clock-policy

## Overview

Validates GPU application clock compliance against a configured policy using NVML telemetry.
For each GPU, the check compares observed graphics and memory application clocks against expected values and classifies drift as `OK`, `WARN`, or `CRITICAL`.

## Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--expected-graphics-freq` | Integer | **Required** | Expected graphics application clock (MHz) |
| `--expected-memory-freq` | Integer | **Required** | Expected memory application clock (MHz) |
| `--warn-delta-mhz` | Integer | 30 | Warn when absolute drift exceeds this threshold |
| `--critical-delta-mhz` | Integer | 75 | Critical when absolute drift exceeds this threshold |
| `--timeout` | Integer | 300 | Command execution timeout in seconds |
| `--sink` | String | do_nothing | Telemetry sink destination |
| `--sink-opts` | Multiple | - | Sink-specific configuration |
| `--verbose-out` | Flag | False | Display detailed output |
| `--log-level` | Choice | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `--log-folder` | String | `/var/log/fb-monitoring` | Log directory |
| `--heterogeneous-cluster-v1` | Flag | False | Enable heterogeneous cluster support |

## Exit Conditions

| Exit Code | Condition |
|-----------|-----------|
| **OK (0)** | Feature flag disabled (killswitch active) |
| **OK (0)** | All GPUs are within thresholds |
| **WARN (1)** | At least one GPU exceeds warn threshold |
| **WARN (1)** | No GPUs detected |
| **CRITICAL (2)** | At least one GPU exceeds critical threshold |
| **UNKNOWN (3)** | Initialization or telemetry flow failed before final classification |

## Feature Flag (Killswitch)

Use the health checks features config to disable this check:

```toml
[HealthChecksFeatures]
disable_nvidia_smi_clock_policy = true
```

## Usage Examples

### Basic Policy Validation

```shell
health_checks check-gpu-clock-policy \
  --expected-graphics-freq 1155 \
  --expected-memory-freq 1593 \
  --warn-delta-mhz 30 \
  --critical-delta-mhz 75 \
  --sink do_nothing \
  [CLUSTER] \
  app
```

### With Telemetry Sink

```shell
health_checks check-gpu-clock-policy \
  --expected-graphics-freq 1155 \
  --expected-memory-freq 1593 \
  --warn-delta-mhz 30 \
  --critical-delta-mhz 75 \
  --sink otel \
  --sink-opts "log_resource_attributes={'attr_1': 'value1'}" \
  [CLUSTER] \
  app
```
