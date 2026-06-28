# CODEX HANDOFF v3.2.3

## Current Delivery

- Version: `3.2.3-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_3.py`
- Bundle SHA256: `66FEA7226435709367008BF1956B0E5D53467FFC30D39D74753985F0AC971107`
- Local verification: `343 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Settlement events now compute option intrinsic cashflow in settlement currency.
- Settlement status is explicit: `COMPUTED`, `ESTIMATED`, or `DATA_GAP`.
- Missing explicit settlement price can use current index as `INDEX_FALLBACK` and marks the result `ESTIMATED`.
- Missing settlement/index price remains fail-visible as `DATA_GAP`; final option PnL is not fabricated.
- Protection recovery now goes through `_apply_protection_recovery_fill()`, recording gross recovery value, fees, and net recovery value.
- Option realized PnL is recomputed from entry net credit, realized exit spend, net protection recovery, and settlement cashflow.
- Closed archives recompute final option PnL fields before saving closed history.
- `POSITION_MANAGE` ledger detail now surfaces settlement, protection recovery, option realized PnL, and final PnL status.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, revoke, or manual hedge runtime commands were added.
- Position management remains non-interactive; hedge/exit/TP are still config-gated and exchange-state driven.
- V32 hedge pending single-flight, unknown-submit guard, Binance position fail-closed, and no legacy submit fallback remain intact.
- This is local code/artifact verification only, not FMZ live proof.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_3.py
```

## Final SHA256 Set

All four bundle files match:

```text
66FEA7226435709367008BF1956B0E5D53467FFC30D39D74753985F0AC971107  realsrc/spm_manual_gate_execution_fmz.py
66FEA7226435709367008BF1956B0E5D53467FFC30D39D74753985F0AC971107  artifacts/spm_manual_gate_execution_fmz.py
66FEA7226435709367008BF1956B0E5D53467FFC30D39D74753985F0AC971107  artifacts/spm_manual_gate_execution_fmz_v3_2_3.py
66FEA7226435709367008BF1956B0E5D53467FFC30D39D74753985F0AC971107  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_3.py
```

## Next Best Small Version

- v3.2.4 should start with real current portfolio inputs for precommit budget. `_current_portfolio()` still returns fixed zeros; replace it with strict account summary + option position reads, and block new entries on account/position/Greek gaps.
- Keep the no-snapshot orphan hedge policy as manual cleanup unless a later release adds ownership-proven reduce-only cleanup with explicit config and tests.
- After one more audit, decide whether legacy hedge helper paths can be deleted without breaking isolated tests.
