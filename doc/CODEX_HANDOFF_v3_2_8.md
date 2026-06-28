# CODEX HANDOFF v3.2.8

## Current Delivery

- Version: `3.2.8-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_8.py`
- Bundle SHA256: `5623A2C193574EBAD725762D24CBFF10506BB75610CA357CE2FB1F26CC1EF108`
- Local verification: `350 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Fully removed the legacy Binance hedge helper `bnc_place_hedge()` from current source and generated bundle surface.
- `exec_hedge_step()` now returns a direct Binance dry-run hedge intent without importing or calling the removed helper.
- Binance live hedge through `exec_hedge_step()` remains fail-closed with `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`; V32 live submissions stay on `bnc_submit_hedge_order()` plus pending-first reconciliation.
- Added an isolation test to prevent `bnc_place_hedge` from reappearing in `binance_io.py` or `execution.py`.
- Updated current README, project rules, open-gap TODO, checksums, and delivery artifact backup to v3.2.8.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_8.py
```

## Final SHA256 Set

All four bundle files match:

```text
5623A2C193574EBAD725762D24CBFF10506BB75610CA357CE2FB1F26CC1EF108  realsrc/spm_manual_gate_execution_fmz.py
5623A2C193574EBAD725762D24CBFF10506BB75610CA357CE2FB1F26CC1EF108  artifacts/spm_manual_gate_execution_fmz.py
5623A2C193574EBAD725762D24CBFF10506BB75610CA357CE2FB1F26CC1EF108  artifacts/spm_manual_gate_execution_fmz_v3_2_8.py
5623A2C193574EBAD725762D24CBFF10506BB75610CA357CE2FB1F26CC1EF108  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_8.py
```

## Next Best Small Version

- Review the remaining proposed-budget reserve placeholder: `hedge_margin_reserve = 0.0`.
- Remove or rewrite stale current docs that still describe runtime authorization prompts.
- Review `realsrc/src/authorization.py` and decide whether to keep it as a legacy pure-function reference or delete it in a dedicated cleanup release.
- Remove or fully implement `HEDGE_MAKER_FIRST_REDUCE_ENABLED`; current config validation still rejects `True`.
