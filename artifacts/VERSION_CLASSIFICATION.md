# Artifact Version Classification

This file defines the release class for generated FMZ bundles in `artifacts/`.

## Formal Live-Validation Release

- `artifacts/spm_manual_gate_execution_fmz_v1.py`
- `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`
- `artifacts/spm_manual_gate_execution_fmz.py` when its SHA256 matches v1

Current v1 SHA256:

`D41E00A122023455FD75E60F2C2A29B7F23B368CCE5C60364674D6EF45ED57FC`

## Test-Round Archives

All previous generated bundles with a `v3*` filename are test-round artifacts,
including:

- `artifacts/spm_manual_gate_execution_fmz_v3_0_*.py`
- `artifacts/spm_manual_gate_execution_fmz_v3_1*.py`
- `artifacts/spm_manual_gate_execution_fmz_v3_2_*.py`

These files are retained only as historical test/audit snapshots. They are not
the formal live-validation release and should not be deployed as the current
sealed artifact.

## Rule

For formal live validation, use only the v1 latest-delivery bundle and verify
the boot log shows `STRATEGY_VERSION = "v1"`.
