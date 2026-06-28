# CODEX HANDOFF v3.2.1

## Current Delivery

- Version: `3.2.1-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_1.py`
- Bundle SHA256: `EB1000DC6EED537393C59AD412D4167CF5D0546F4CD57FFA10A60B8EE3908824`
- Local verification: `328 passed, 0 failed`; `realsrc/build_bundle.py --check` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Added `dbt_get_positions_strict()`: successful reads return a list; API/transport failures return `None`.
- Startup recovery now fail-closes with `OPTION_POSITION_QUERY_FAILED` when option-position read fails, and it does not finalize settled legs from a data gap.
- `manage_cycle()` now surfaces option-position read failure as reconcile/data-gap detail instead of passing a fake empty position list into settlement reconciliation.
- `_settlement_reconcile_snapshot()` refuses to finalize when `option_positions is None`.
- `_archive_closed()` now returns a boolean, refuses to archive while hedge policy has a pending order, clears `_RECOVERY_KEY` to OK only after a real archive, and resets hedge policy state.
- No-snapshot orphan hedge recovery now has an explicit `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` phase and read-screen detail. It remains manual cleanup only; no automatic external perp close was added.
- Settled / short-flat positions skip short-leg risk quoting and return `OPTION_SETTLED_NO_SHORT_RISK`.
- Added `doc/OPEN_GAPS_TODO.md` as the ongoing work queue for known gaps, redundancies, and optimization candidates.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, revoke, or manual hedge runtime commands were added.
- Settlement read failure is now safer than v3.2.0: it blocks recovery/settlement finalization instead of pretending the exchange returned empty positions.
- No-snapshot orphan hedge cleanup is display/manual-only in this version; no automatic reduce-only cleanup is attempted without ownership evidence.
- PnL completion is not claimed. Settlement cashflow, protection recovery value, final option PnL, and real portfolio budget remain queued in `doc/OPEN_GAPS_TODO.md`.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_1.py
```

## Final SHA256 Set

All four bundle files match:

```text
EB1000DC6EED537393C59AD412D4167CF5D0546F4CD57FFA10A60B8EE3908824  realsrc/spm_manual_gate_execution_fmz.py
EB1000DC6EED537393C59AD412D4167CF5D0546F4CD57FFA10A60B8EE3908824  artifacts/spm_manual_gate_execution_fmz.py
EB1000DC6EED537393C59AD412D4167CF5D0546F4CD57FFA10A60B8EE3908824  artifacts/spm_manual_gate_execution_fmz_v3_2_1.py
EB1000DC6EED537393C59AD412D4167CF5D0546F4CD57FFA10A60B8EE3908824  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_1.py
```

## Next Best Small Version

- v3.2.2 should start with settlement cashflow and protection recovery accounting, with failing tests for OTM/ITM short, ITM long, both-ITM vertical, missing settlement price, and fallback-index `ESTIMATED` status.
- Keep `doc/OPEN_GAPS_TODO.md` updated before and after each small-version release.
