# CODEX HANDOFF v3.1.5

## Current Delivery

- Version: `3.1.5-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_5.py`
- Bundle SHA256: `89B40DF025270751B9A632784416889D9E3D1053950288061DCBC170118E8046`
- Local verification: `311 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Wired option-settlement reconciliation into both startup recovery and normal `POSITION_MANAGE`.
- A local option leg is finalized only when both conditions hold:
  - the leg expiry is older than `SETTLEMENT_RECONCILE_GRACE_MS`,
  - the current exchange option-position read succeeds and the matching instrument is absent/zero.
- Short-leg settlement sets `remaining_short_qty = 0.0`, records an `option_settlement_history` entry, and leaves settlement PnL as `settlement_pnl_status = NOT_COMPUTED`.
- If startup recovery sees a settled short with an existing perp hedge, it now returns `ORPHAN_HEDGE_EMERGENCY` with `SETTLED_OPTION_WITH_PERP_HEDGE` instead of blocking on `RECORD_SHORT_BUT_NO_EXCHANGE_OPTION`.
- Settled shorts force hedge target zero and route existing perp exposure through reduce-only orphan cleanup.
- Short-flat take-profit evaluation no longer quotes the expired short instrument, so settlement cleanup is not blocked by stale option market data.
- Entry snapshots now persist `long_expiry_ts` through the recommendation and position snapshot path.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, or revoke runtime commands were added.
- Ordinary 80% TP still has the last-3h DTE gate; risk exit and hedge are not blocked by that gate.
- `LogStatus` remains the primary trader screen; ordinary `POSITION_MANAGE` cycles do not spam `Log`.
- Missing Binance position/PnL/depth data is not rendered as zero.
- Settlement does not synthesize or claim realized settlement PnL.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_5.py
```

## Final SHA256 Set

All four bundle files match:

```text
89B40DF025270751B9A632784416889D9E3D1053950288061DCBC170118E8046  realsrc/spm_manual_gate_execution_fmz.py
89B40DF025270751B9A632784416889D9E3D1053950288061DCBC170118E8046  artifacts/spm_manual_gate_execution_fmz.py
89B40DF025270751B9A632784416889D9E3D1053950288061DCBC170118E8046  artifacts/spm_manual_gate_execution_fmz_v3_1_5.py
89B40DF025270751B9A632784416889D9E3D1053950288061DCBC170118E8046  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_5.py
```

## Next Best Small Checks

- Replay a real Deribit expiry/settlement log once the user provides FMZ/exchange evidence, especially option-position shape after settlement.
- Add realized settlement PnL only from exchange bill/ledger evidence, not from inferred mark or expiry value.
- Continue the hedge-trigger optimization audit separately; this delivery only closes the settlement-to-orphan-hedge handoff gap.
