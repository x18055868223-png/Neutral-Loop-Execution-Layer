# Codex Handoff v1

## Release

- Version: `v1`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v1.py`
- Latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`
- SHA256: `D41E00A122023455FD75E60F2C2A29B7F23B368CCE5C60364674D6EF45ED57FC`
- Release class: formal live-validation release. All `v3*` bundles are
  historical test-round archives.
- Boundary: local verification only. This is not FMZ live proof.

## Why This Version Exists

v1 is the formal small-size live-validation artifact after the public Deribit
option fill-scenario audit. It keeps the v3.2.28 safety skeleton and changes
only the live-fill adaptation parameters and the operator read surface.

## Changes

- `STRATEGY_VERSION` is now `v1`.
- Protection leg keeps mark-derived persistent maker first.
- Protection controlled taker fallback now triggers after `60` seconds, only
  when visible ask depth covers the remaining amount and the net-credit floor
  still passes.
- Short leg remains blocked until confirmed protection fill coverage exists.
- Short leg maker wait is now `15` seconds by default.
- `LogStatus` protection-order line now shows elapsed wait, fallback threshold,
  remaining time, and maker/taker-fallback state.

## Tests Added First

- `test_entry_protection_default_v1_fallback_takes_after_sixty_seconds`
  verifies the default 60-second protection fallback.
- `test_entry_protection_order_line_surfaces_fallback_budget` verifies the
  status-line wait budget.
- `test_default_config_is_live_ready_without_legacy_operator_fields` now locks
  `STRATEGY_VERSION = "v1"`, protection fallback `60`, and short wait `15`.

Initial RED evidence:

- Full local suite failed with 3 expected failures before implementation:
  version still `3.2.28-manual-gate`, fallback still `600`, and display did not
  include fallback threshold/remaining seconds.

## Verification

- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `403 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- Delivery files refreshed:
  `realsrc/spm_manual_gate_execution_fmz.py`,
  `artifacts/spm_manual_gate_execution_fmz.py`,
  `artifacts/spm_manual_gate_execution_fmz_v1.py`,
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`.

## Live Validation Notes

- Use only the latest-delivery file for FMZ deployment.
- Confirm FMZ shows `STRATEGY_VERSION = "v1"` at boot.
- During first entry attempt, watch the protection-order row for elapsed,
  threshold, remaining, and fallback state.
- Treat local green tests as live-test readiness, not live proof. FMZ live
  acceptance still requires saved FMZ logs and exchange-state snapshots.
