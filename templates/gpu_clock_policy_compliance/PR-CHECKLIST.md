# PR Checklist - GPU Clock Policy Compliance

## PR 1 - Schema and policy evaluation
- [ ] Add/validate policy dataclasses
- [ ] Add unit tests for severity boundaries
- [ ] Add negative test for invalid thresholds

## PR 2 - Health check integration
- [ ] Add command-line options
- [ ] Integrate telemetry output fields
- [ ] Add command-level tests for OK/WARN/CRITICAL

## PR 3 - Rollout hardening
- [ ] Add config-driven defaults
- [ ] Add docs in health check README
- [ ] Add dashboard runbook links
