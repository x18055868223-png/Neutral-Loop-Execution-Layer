# CODEX HANDOFF v3.2.13

## Current Delivery

- Version: `3.2.13-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_13.py`
- Bundle SHA256: `CCDB04486D9D7907A9CDF9EDE3513274C3D29AAC80C6944A72A0B84AECEB2B60`
- Local verification: `349 passed, 0 failed`; bundle check passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- V32 hedge policy detail now carries crash reference observability:
  `crash_ref_price`, `crash_ref_age_seconds`, and `crash_adverse_bps`.
- `_build_hedge_detail()` forwards those fields into `POSITION_MANAGE`.
- `风险与对冲` renders a `Crash观测` row with reference price, reference age, and adverse move bps.
- This is observability only. No hedge gate, trigger threshold, submit path, or native conditional order behavior changed.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- Position management remains non-interactive; hedge/exit/TP are still config-gated and exchange-state driven.
- Binance V32 hedge remains pending-first and single-flight.
- This is local code/artifact verification only, not FMZ live proof.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_13.py
```

## Final SHA256 Set

- `realsrc/spm_manual_gate_execution_fmz.py`: `CCDB04486D9D7907A9CDF9EDE3513274C3D29AAC80C6944A72A0B84AECEB2B60`
- `artifacts/spm_manual_gate_execution_fmz.py`: `CCDB04486D9D7907A9CDF9EDE3513274C3D29AAC80C6944A72A0B84AECEB2B60`
- `artifacts/spm_manual_gate_execution_fmz_v3_2_13.py`: `CCDB04486D9D7907A9CDF9EDE3513274C3D29AAC80C6944A72A0B84AECEB2B60`
- `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_13.py`: `CCDB04486D9D7907A9CDF9EDE3513274C3D29AAC80C6944A72A0B84AECEB2B60`

## Next Best Small Version

- Clarify or rename `HEDGE_REDUCTION_RATIO` so gamma-aware default sizing is not misread.
