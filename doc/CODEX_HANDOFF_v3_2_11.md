# CODEX HANDOFF v3.2.11

## Current Delivery

- Version: `3.2.11-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_11.py`
- Bundle SHA256: `3BAC47A8FC4DD52C72A3AA8486A6CA5B5A28D31DDDBCD6EF6C1815874FBB3ADF`
- Local verification: `346 passed, 0 failed`; bundle check passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Removed `HEDGE_MAKER_FIRST_REDUCE_ENABLED`; maker-first reduce remains deliberately unimplemented and absent from the current config surface.
- Removed unused hedge config switches: `HEDGE_SLIPPAGE_GUARD_ENABLED`, `HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA`, and `HEDGE_SLIP_ALERT_BPS`.
- Kept `HEDGE_EPISODE_COST_ALERT_BPS` because it is wired as an observability threshold and does not block HARD hedge actions.
- Updated tests so unimplemented hedge switches cannot return silently.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_11.py
```

## Final SHA256 Set

- `realsrc/spm_manual_gate_execution_fmz.py`: `3BAC47A8FC4DD52C72A3AA8486A6CA5B5A28D31DDDBCD6EF6C1815874FBB3ADF`
- `artifacts/spm_manual_gate_execution_fmz.py`: `3BAC47A8FC4DD52C72A3AA8486A6CA5B5A28D31DDDBCD6EF6C1815874FBB3ADF`
- `artifacts/spm_manual_gate_execution_fmz_v3_2_11.py`: `3BAC47A8FC4DD52C72A3AA8486A6CA5B5A28D31DDDBCD6EF6C1815874FBB3ADF`
- `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_11.py`: `3BAC47A8FC4DD52C72A3AA8486A6CA5B5A28D31DDDBCD6EF6C1815874FBB3ADF`

## Next Best Small Version

- Review remaining Deribit hedge compatibility branch and fallback sizing constants; keep Deribit option entry/exit/quote logic separate.
- Clarify or rename `HEDGE_REDUCTION_RATIO` so gamma-aware default sizing is not misread.
- Consider crash reference age/price display as observability only.
