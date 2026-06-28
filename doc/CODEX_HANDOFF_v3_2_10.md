# CODEX HANDOFF v3.2.10

## Current Delivery

- Version: `3.2.10-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_10.py`
- Bundle SHA256: `76361BC13C5B1BA2A4F6E0B34E3B9BC8898132E72FD49D1BAF26C6F25727EE68`
- Local verification: `346 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Removed the obsolete source-only `realsrc/src/authorization.py` module.
- Removed the old authorization-only test file that kept TP/risk-exit authorization semantics alive as a standalone surface.
- Added a source isolation regression test so the runtime authorization module cannot be reintroduced beside the confirmation-code-only command router.
- Re-scanned current docs: current continuation docs state confirmation-code-only interaction; historical handoffs remain historical.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_10.py
```

## Final SHA256 Set

All four bundle files match:

```text
76361BC13C5B1BA2A4F6E0B34E3B9BC8898132E72FD49D1BAF26C6F25727EE68  realsrc/spm_manual_gate_execution_fmz.py
76361BC13C5B1BA2A4F6E0B34E3B9BC8898132E72FD49D1BAF26C6F25727EE68  artifacts/spm_manual_gate_execution_fmz.py
76361BC13C5B1BA2A4F6E0B34E3B9BC8898132E72FD49D1BAF26C6F25727EE68  artifacts/spm_manual_gate_execution_fmz_v3_2_10.py
76361BC13C5B1BA2A4F6E0B34E3B9BC8898132E72FD49D1BAF26C6F25727EE68  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_10.py
```

## Next Best Small Version

- Remove or fully implement `HEDGE_MAKER_FIRST_REDUCE_ENABLED`; current config validation still rejects `True`.
- Continue scanning for dead or misleading hedge config fields, but keep changes small and test-backed.
