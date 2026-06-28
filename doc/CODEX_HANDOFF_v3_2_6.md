# CODEX HANDOFF v3.2.6

## Current Delivery

- Version: `3.2.6-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_6.py`
- Bundle SHA256: `73218774150864F94AE130192D686E5EBCCE8E17A131EC0FB3EAE7E7648A989B`
- Local verification: `351 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- The no-snapshot orphan hedge policy is now explicit and permanent as manual cleanup only.
- `_orphan_hedge_cleanup_detail()` exposes `policy=MANUAL_CLEANUP_ONLY`.
- `_orphan_hedge_cleanup_detail()` exposes `auto_cleanup_allowed=False`.
- Added regression coverage so `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` cannot silently lose those policy fields.
- Updated the open-gap TODO: this item is closed in v3.2.6, while legacy helper cleanup and budget reserve work remain open.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, revoke, or manual hedge runtime commands were added.
- Position management remains non-interactive; hedge/exit/TP are still config-gated and exchange-state driven.
- No automatic no-snapshot external perp close was added. Unknown orphan hedge exposure remains manual reduce-only cleanup.
- V32 hedge pending single-flight, unknown-submit guard, Binance position fail-closed, and no legacy submit fallback remain intact.
- This is local code/artifact verification only, not FMZ live proof.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_6.py
```

## Final SHA256 Set

All four bundle files match:

```text
73218774150864F94AE130192D686E5EBCCE8E17A131EC0FB3EAE7E7648A989B  realsrc/spm_manual_gate_execution_fmz.py
73218774150864F94AE130192D686E5EBCCE8E17A131EC0FB3EAE7E7648A989B  artifacts/spm_manual_gate_execution_fmz.py
73218774150864F94AE130192D686E5EBCCE8E17A131EC0FB3EAE7E7648A989B  artifacts/spm_manual_gate_execution_fmz_v3_2_6.py
73218774150864F94AE130192D686E5EBCCE8E17A131EC0FB3EAE7E7648A989B  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_6.py
```

## Next Best Small Version

- Audit whether legacy hedge helper paths can be deleted without breaking isolated tests.
- Review the remaining proposed-budget reserve placeholder: `hedge_margin_reserve = 0.0`.
- Remove or rewrite stale current docs that still describe runtime authorization prompts.
