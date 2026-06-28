# CODEX HANDOFF v3.2.9

## Current Delivery

- Version: `3.2.9-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_9.py`
- Bundle SHA256: `B84133F16E987D18BF25F4254D2B04B8E4BE2DF4B9CD6BAFD3DB37A3CA791847`
- Local verification: `351 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Replaced the remaining precommit `hedge_margin_reserve = 0.0` placeholder.
- `_build_precommit_live()` now computes proposed hedge reserve from the new structure's option net delta and `HEDGE_MARGIN_RESERVE_RATE`.
- When current margin usage is reported as `initial_margin/equity`, the reserve is normalized by account equity so it shares the same projected-budget unit.
- Missing proposed delta or required account equity fails closed through the existing `BUDGET_INPUT_INCOMPLETE` path instead of silently using zero.
- Added a regression test proving the reserve flows into projected margin usage.

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
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_9.py
```

## Final SHA256 Set

All four bundle files match:

```text
B84133F16E987D18BF25F4254D2B04B8E4BE2DF4B9CD6BAFD3DB37A3CA791847  realsrc/spm_manual_gate_execution_fmz.py
B84133F16E987D18BF25F4254D2B04B8E4BE2DF4B9CD6BAFD3DB37A3CA791847  artifacts/spm_manual_gate_execution_fmz.py
B84133F16E987D18BF25F4254D2B04B8E4BE2DF4B9CD6BAFD3DB37A3CA791847  artifacts/spm_manual_gate_execution_fmz_v3_2_9.py
B84133F16E987D18BF25F4254D2B04B8E4BE2DF4B9CD6BAFD3DB37A3CA791847  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_9.py
```

## Next Best Small Version

- Remove or rewrite stale current docs that still describe runtime authorization prompts.
- Review `realsrc/src/authorization.py` and decide whether to keep it as a legacy pure-function reference or delete it in a dedicated cleanup release.
- Remove or fully implement `HEDGE_MAKER_FIRST_REDUCE_ENABLED`; current config validation still rejects `True`.
