# Codex Handoff v3.2.14

## Release

- Version: `3.2.14-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_14.py`
- Latest delivery at release time:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_14.py`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- TEST profile dry-run boundary: V32 hedge cleanup can still bypass the ordinary
  hedge gate when it is reduce-only cleanup, but submit now receives
  `allow_live=False` unless `RUN_PROFILE` normalizes to `LIVE`.
- Ledger drift recovery: `run_cycle()` now treats a persisted `_POSITION_KEY`
  snapshot as an active position even when the local ledger state has fallen
  back to `NO_POSITION`, so the trader is not returned to the entry-planning
  screen while a managed position snapshot exists.
- Test maintenance: the startup recovery re-read test now matches the current
  Binance hedge default while preserving the same recovery-block assertion.

## Tests Added First

- `test_test_profile_orphan_hedge_cleanup_stays_dry_even_when_gate_bypassed`
  failed before the fix because `_hedge_policy_submit()` received
  `allow_live=True` under `RUN_PROFILE=TEST`.
- `test_run_cycle_position_snapshot_overrides_lost_no_position_state` failed
  before the fix because an existing `_POSITION_KEY` snapshot with
  `ledger_get_state()==NO_POSITION` still went to `PLAN_MENU_READY`.

## Verification

- Targeted red tests reproduced both gaps before implementation.
- Targeted tests passed after implementation.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `351 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> syntax compile passed; bundle smoke passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_14.py`
  -> passed.

## Remaining For Next Small Version

- Make V32 episode-cost display explicit that the field is reserved telemetry,
  not computed realized cost.
- Verify/fix taker buy tick rounding so best-ask fallback orders cross after
  rounding.
