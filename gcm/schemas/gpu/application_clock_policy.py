# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
from dataclasses import dataclass
from enum import Enum

from gcm.schemas.gpu.application_clock import ApplicationClockInfo


class ClockComplianceSeverity(Enum):
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"



@dataclass(frozen=True)
class ClockPolicy:
    expected_graphics_freq: int
    expected_memory_freq: int
    warn_delta_mhz: int = 0
    critical_delta_mhz: int = 0

    def __post_init__(self) -> None:
        if self.warn_delta_mhz < 0:
            raise ValueError("warn_delta_mhz must be >= 0")
        if self.critical_delta_mhz < self.warn_delta_mhz:
            raise ValueError(
                "critical_delta_mhz must be >= warn_delta_mhz for consistent policy thresholds"
            )


@dataclass(frozen=True)
class ClockComplianceResult:
    observed: ApplicationClockInfo
    policy: ClockPolicy
    graphics_delta_mhz: int
    memory_delta_mhz: int
    severity: ClockComplianceSeverity

    @property
    def compliant(self) -> bool:
        return self.severity == ClockComplianceSeverity.OK


def evaluate_clock_policy(
    observed: ApplicationClockInfo, policy: ClockPolicy
) -> ClockComplianceResult:
    graphics_delta_mhz = abs(observed.graphics_freq - policy.expected_graphics_freq)
    memory_delta_mhz = abs(observed.memory_freq - policy.expected_memory_freq)
    max_delta_mhz = max(graphics_delta_mhz, memory_delta_mhz)

    if max_delta_mhz >= policy.critical_delta_mhz:
        severity = ClockComplianceSeverity.CRITICAL
    elif max_delta_mhz >= policy.warn_delta_mhz:
        severity = ClockComplianceSeverity.WARN
    else:
        severity = ClockComplianceSeverity.OK

    return ClockComplianceResult(
        observed=observed,
        policy=policy,
        graphics_delta_mhz=graphics_delta_mhz,
        memory_delta_mhz=memory_delta_mhz,
        severity=severity,
    )
