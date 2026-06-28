# CODEX HANDOFF v3.2.12

## Current Delivery

- Version: `3.2.12-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_12.py`
- Bundle SHA256: `338787F1FBDFD30BE84991ACA7418280E3CC90DEA62A7DB5C8407801206B238B`
- Local verification: `348 passed, 0 failed`; bundle check passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Removed Deribit perpetual hedge fallback sizing constants from the current config surface:
  `HEDGE_CONTRACT_SIZE_FALLBACK` and `HEDGE_MIN_TRADE_FALLBACK`.
- `_evaluate_hedge()` now fails closed with `UNSUPPORTED_HEDGE_VENUE` for non-Binance hedge venues instead of reading Deribit perp state or estimating a fallback target.
- `exec_hedge_step()` now blocks legacy Deribit perp hedge live execution before any quote/order call.
- Deribit option entry, exit, quote, settlement, and recovery logic were not changed.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- Position management remains non-interactive; hedge/exit/TP are still config-gated and exchange-state driven.
- Binance V32 hedge remains the only live automatic hedge submit path and keeps pending-first single-flight reconciliation.
- This is local code/artifact verification only, not FMZ live proof.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_12.py
```

## Final SHA256 Set

- `realsrc/spm_manual_gate_execution_fmz.py`: `338787F1FBDFD30BE84991ACA7418280E3CC90DEA62A7DB5C8407801206B238B`
- `artifacts/spm_manual_gate_execution_fmz.py`: `338787F1FBDFD30BE84991ACA7418280E3CC90DEA62A7DB5C8407801206B238B`
- `artifacts/spm_manual_gate_execution_fmz_v3_2_12.py`: `338787F1FBDFD30BE84991ACA7418280E3CC90DEA62A7DB5C8407801206B238B`
- `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_12.py`: `338787F1FBDFD30BE84991ACA7418280E3CC90DEA62A7DB5C8407801206B238B`

## Next Best Small Version

- Clarify or rename `HEDGE_REDUCTION_RATIO` so gamma-aware default sizing is not misread.
- Consider crash reference age/price display as observability only.
