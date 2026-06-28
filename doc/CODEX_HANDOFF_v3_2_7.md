# CODEX HANDOFF v3.2.7

## Current Delivery

- Version: `3.2.7-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_7.py`
- Bundle SHA256: `2384D22123F77AAA7CB6856A777A00327AD32FFEE664972D3CCAD9D1218F503C`
- Local verification: `352 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- The legacy Binance helper `bnc_place_hedge()` is no longer live-capable.
- Live calls to `bnc_place_hedge()` return `LEGACY_HEDGE_HELPER_LIVE_DISABLED` without probing the exchange.
- `exec_hedge_step()` no longer bridges Binance live hedge execution into the legacy helper path; it returns `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`.
- Binance prompt-limit live submit coverage now targets `bnc_submit_hedge_order()`, which is the V32 pending-first controller entry.
- Removed the old submit-sleep-query-cancel live body from `bnc_place_hedge()`.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_7.py
```

## Final SHA256 Set

All four bundle files match:

```text
2384D22123F77AAA7CB6856A777A00327AD32FFEE664972D3CCAD9D1218F503C  realsrc/spm_manual_gate_execution_fmz.py
2384D22123F77AAA7CB6856A777A00327AD32FFEE664972D3CCAD9D1218F503C  artifacts/spm_manual_gate_execution_fmz.py
2384D22123F77AAA7CB6856A777A00327AD32FFEE664972D3CCAD9D1218F503C  artifacts/spm_manual_gate_execution_fmz_v3_2_7.py
2384D22123F77AAA7CB6856A777A00327AD32FFEE664972D3CCAD9D1218F503C  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_7.py
```

## Next Best Small Version

- Review the remaining proposed-budget reserve placeholder: `hedge_margin_reserve = 0.0`.
- Remove or rewrite stale current docs that still describe runtime authorization prompts.
- Fully delete `bnc_place_hedge()` after any remaining dry-run tests are migrated away from the helper.
