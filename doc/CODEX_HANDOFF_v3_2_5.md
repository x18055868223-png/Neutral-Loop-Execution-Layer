# CODEX HANDOFF v3.2.5

## Current Delivery

- Version: `3.2.5-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_5.py`
- Bundle SHA256: `54BBE8D00C4D653CCBF35262D8B0A628DB70ED56E6E5FFFBB6E2F49A891485DA`
- Local verification: `351 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- `exec_quote()` now carries option `vega` from Deribit ticker greeks.
- `_build_precommit_live()` no longer defaults missing proposed short gamma to zero.
- `_build_precommit_live()` no longer defaults proposed short vega to zero.
- Missing proposed option Greeks now flow into `evaluate_projected_budget()` as incomplete inputs and block with `BUDGET_INPUT_INCOMPLETE`.
- Added regression coverage for vega propagation and proposed short-vega fail-closed behavior.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_5.py
```

## Final SHA256 Set

All four bundle files match:

```text
54BBE8D00C4D653CCBF35262D8B0A628DB70ED56E6E5FFFBB6E2F49A891485DA  realsrc/spm_manual_gate_execution_fmz.py
54BBE8D00C4D653CCBF35262D8B0A628DB70ED56E6E5FFFBB6E2F49A891485DA  artifacts/spm_manual_gate_execution_fmz.py
54BBE8D00C4D653CCBF35262D8B0A628DB70ED56E6E5FFFBB6E2F49A891485DA  artifacts/spm_manual_gate_execution_fmz_v3_2_5.py
54BBE8D00C4D653CCBF35262D8B0A628DB70ED56E6E5FFFBB6E2F49A891485DA  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_5.py
```

## Next Best Small Version

- Decide the no-snapshot orphan hedge policy: keep manual cleanup as permanent policy, or add ownership-proven reduce-only cleanup with explicit config and tests.
- Audit whether legacy hedge helper paths can be deleted without breaking isolated tests.
- Review the remaining proposed-budget reserve placeholder: `hedge_margin_reserve = 0.0`.
