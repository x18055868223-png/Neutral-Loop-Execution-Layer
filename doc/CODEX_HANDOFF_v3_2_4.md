# CODEX HANDOFF v3.2.4

## Current Delivery

- Version: `3.2.4-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_4.py`
- Bundle SHA256: `068032EC3B0B7883E53E0922BBEB4A279089DA2939C966F7C1D89434D4351644`
- Local verification: `349 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- `_current_portfolio()` no longer returns fixed zero load for projected-budget checks.
- Current portfolio budget inputs now come from strict Deribit account summary and option-position reads.
- Account summary failure returns `ACCOUNT_SUMMARY_QUERY_FAILED`.
- Missing account initial-margin input returns `ACCOUNT_MARGIN_DATA_GAP`.
- Strict option-position read failure returns `OPTION_POSITION_QUERY_FAILED`.
- Option position size gaps return `OPTION_POSITION_SIZE_DATA_GAP`.
- Short-option Greek gaps return `OPTION_GREEK_DATA_GAP` with the instrument name when available.
- Short-option current load now accumulates absolute gamma and vega by short amount.
- `_build_precommit_live()` converts current-portfolio data gaps into a fail-closed `ProjectedBudgetPackage` with `decision=BLOCK`.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_4.py
```

## Final SHA256 Set

All four bundle files match:

```text
068032EC3B0B7883E53E0922BBEB4A279089DA2939C966F7C1D89434D4351644  realsrc/spm_manual_gate_execution_fmz.py
068032EC3B0B7883E53E0922BBEB4A279089DA2939C966F7C1D89434D4351644  artifacts/spm_manual_gate_execution_fmz.py
068032EC3B0B7883E53E0922BBEB4A279089DA2939C966F7C1D89434D4351644  artifacts/spm_manual_gate_execution_fmz_v3_2_4.py
068032EC3B0B7883E53E0922BBEB4A279089DA2939C966F7C1D89434D4351644  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_4.py
```

## Next Best Small Version

- Decide the no-snapshot orphan hedge policy: keep manual cleanup as permanent policy, or add ownership-proven reduce-only cleanup with explicit config and tests.
- Audit whether legacy hedge helper paths can be deleted without breaking isolated tests.
- Review remaining placeholder proposed-budget fields: `short_vega = 0.0` and `hedge_margin_reserve = 0.0`.
