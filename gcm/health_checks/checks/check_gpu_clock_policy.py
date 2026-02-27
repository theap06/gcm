# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
import logging
import os
import socket
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Collection, Optional, Protocol

import click

import gni_lib
from gcm.health_checks.check_utils.output_context_manager import OutputContext
from gcm.health_checks.check_utils.telem import TelemetryContext
from gcm.health_checks.click import common_arguments, telemetry_argument
from gcm.health_checks.device_telemetry_exception_handling import (
    handle_device_telemetry_exception,
)
from gcm.health_checks.types import CHECK_TYPE, CheckEnv, ExitCode, LOG_LEVEL
from gcm.monitoring.click import heterogeneous_cluster_v1_option
from gcm.monitoring.device_telemetry_client import (
    DeviceTelemetryClient,
    DeviceTelemetryException,
)
from gcm.monitoring.device_telemetry_nvml import NVMLDeviceTelemetryClient
from gcm.monitoring.features.gen.generated_features_healthchecksfeatures import (
    FeatureValueHealthChecksFeatures,
)
from gcm.monitoring.slurm.derived_cluster import get_derived_cluster
from gcm.monitoring.utils.monitor import init_logger
from gcm.schemas.gpu.application_clock_policy import (
    ClockComplianceResult,
    ClockComplianceSeverity,
    ClockPolicy,
    evaluate_clock_policy,
)
from gcm.schemas.health_check.health_check_name import HealthCheckName
from typeguard import typechecked


class GpuClockPolicyCli(CheckEnv, Protocol):
    def get_device_telemetry(self) -> DeviceTelemetryClient: ...


@dataclass
class GpuClockPolicyCliImpl:
    cluster: str
    type: str
    log_level: str
    log_folder: str

    def get_device_telemetry(self) -> DeviceTelemetryClient:
        return NVMLDeviceTelemetryClient()


def severity_to_exitcode(severity: ClockComplianceSeverity) -> ExitCode:
    if severity == ClockComplianceSeverity.CRITICAL:
        return ExitCode.CRITICAL
    if severity == ClockComplianceSeverity.WARN:
        return ExitCode.WARN
    return ExitCode.OK


@click.command()
@common_arguments
@telemetry_argument
@heterogeneous_cluster_v1_option
@click.option(
    "--expected-graphics-freq",
    type=click.IntRange(min=0),
    required=True,
    help="Expected GPU graphics application clock frequency (MHz).",
)
@click.option(
    "--expected-memory-freq",
    type=click.IntRange(min=0),
    required=True,
    help="Expected GPU memory application clock frequency (MHz).",
)
@click.option(
    "--warn-delta-mhz",
    type=click.IntRange(min=0),
    default=30,
    show_default=True,
    help="Warn if absolute drift from policy exceeds this many MHz.",
)
@click.option(
    "--critical-delta-mhz",
    type=click.IntRange(min=0),
    default=75,
    show_default=True,
    help="Critical if absolute drift from policy exceeds this many MHz.",
)
@click.pass_obj
@typechecked
def check_gpu_clock_policy(
    obj: Optional[GpuClockPolicyCli],
    cluster: str,
    type: CHECK_TYPE,
    log_level: LOG_LEVEL,
    log_folder: str,
    sink: str,
    sink_opts: Collection[str],
    verbose_out: bool,
    heterogeneous_cluster_v1: bool,
    expected_graphics_freq: int,
    expected_memory_freq: int,
    warn_delta_mhz: int,
    critical_delta_mhz: int,
) -> None:
    """
    Template check for GPU application clock policy compliance and drift detection.

    This command compares observed per-GPU application clocks against an expected
    policy and reports drift severity.
    """
    node: str = socket.gethostname()
    logger, _ = init_logger(
        logger_name=type,
        log_dir=os.path.join(log_folder, type + "_logs"),
        log_name=node + ".log",
        log_level=getattr(logging, log_level),
    )

    logger.info(
        "check_gpu_clock_policy: "
        f"cluster: {cluster}, node: {node}, type: {type}, "
        f"expected_graphics_freq: {expected_graphics_freq}, "
        f"expected_memory_freq: {expected_memory_freq}, "
        f"warn_delta_mhz: {warn_delta_mhz}, critical_delta_mhz: {critical_delta_mhz}"
    )

    try:
        gpu_node_id = gni_lib.get_gpu_node_id()
    except Exception as e:
        gpu_node_id = None
        logger.warning(f"Could not get gpu_node_id, likely not a GPU host: {e}")

    derived_cluster = get_derived_cluster(
        cluster=cluster,
        heterogeneous_cluster_v1=heterogeneous_cluster_v1,
        data={"Node": node},
    )

    if obj is None:
        obj = GpuClockPolicyCliImpl(cluster, type, log_level, log_folder)

    if critical_delta_mhz < warn_delta_mhz:
        raise click.BadParameter(
            "critical-delta-mhz must be greater than or equal to warn-delta-mhz",
            param_hint="--critical-delta-mhz",
        )

    policy = ClockPolicy(
        expected_graphics_freq=expected_graphics_freq,
        expected_memory_freq=expected_memory_freq,
        warn_delta_mhz=warn_delta_mhz,
        critical_delta_mhz=critical_delta_mhz,
    )

    exit_code = ExitCode.UNKNOWN
    msg = ""

    with ExitStack() as s:
        s.enter_context(
            TelemetryContext(
                sink=sink,
                sink_opts=sink_opts,
                logger=logger,
                cluster=cluster,
                derived_cluster=derived_cluster,
                type=type,
                name=HealthCheckName.NVIDIA_SMI_CLOCK_POLICY.value,
                node=node,
                get_exit_code_msg=lambda: (exit_code, msg),
                gpu_node_id=gpu_node_id,
            )
        )
        s.enter_context(
            OutputContext(
                type,
                HealthCheckName.NVIDIA_SMI_CLOCK_POLICY,
                lambda: (exit_code, msg),
                verbose_out,
            )
        )

        ff = FeatureValueHealthChecksFeatures()
        if ff.get_healthchecksfeatures_disable_nvidia_smi_clock_policy():
            exit_code = ExitCode.OK
            msg = (
                f"{HealthCheckName.NVIDIA_SMI_CLOCK_POLICY.value} "
                "is disabled by killswitch."
            )
            logger.info(msg)
            sys.exit(exit_code.value)

        try:
            device_telemetry = obj.get_device_telemetry()
            device_count = device_telemetry.get_device_count()
        except DeviceTelemetryException as e:
            exit_code, msg = handle_device_telemetry_exception(e)
            logger.info(msg)
            sys.exit(exit_code.value)

        if device_count == 0:
            exit_code = ExitCode.WARN
            msg = "clock_policy check: No GPUs were detected on this host."
            logger.info(msg)
            sys.exit(exit_code.value)

        results: list[ClockComplianceResult] = []
        for device in range(device_count):
            try:
                handle = device_telemetry.get_device_by_index(device)
                observed = handle.get_clock_freq()
            except DeviceTelemetryException as e:
                error_code, error_msg = handle_device_telemetry_exception(e)
                if error_code > exit_code:
                    exit_code = error_code
                msg += f"clock_policy check: GPU {device}: {error_msg}"
                continue

            result = evaluate_clock_policy(observed, policy)
            results.append(result)
            device_exit_code = severity_to_exitcode(result.severity)
            if device_exit_code > exit_code:
                exit_code = device_exit_code

            msg += (
                "clock_policy check: "
                f"GPU {device}, severity={result.severity.value}, "
                f"expected=(graphics:{policy.expected_graphics_freq}, memory:{policy.expected_memory_freq}), "
                f"observed=(graphics:{result.observed.graphics_freq}, memory:{result.observed.memory_freq}), "
                f"delta_mhz=(graphics:{result.graphics_delta_mhz}, memory:{result.memory_delta_mhz})\n"
            )

        if not results and exit_code == ExitCode.UNKNOWN:
            exit_code = ExitCode.WARN
            msg = "clock_policy check: No GPU clock observations were collected."

        if exit_code == ExitCode.UNKNOWN:
            exit_code = ExitCode.OK

        logger.info(f"{exit_code=}. {msg}")
        sys.exit(exit_code.value)
