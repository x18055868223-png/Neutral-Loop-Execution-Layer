# CODEX HANDOFF v3.1.4

## Current Delivery

- Version: `3.1.4-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_4.py`
- Bundle SHA256: `AD586FA029B6B5D8DA50D05F48A2F3CFE1D330EA49CD41BBD8240312E973B0DA`
- Local verification: `304 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Added the Binance BTCUSDC hedge V313 reconciliation controller, delivered under strategy version `3.1.4`.
- Default `HEDGE_POLICY_V313_ENABLED = True`; Deribit and `False` keep the legacy one-step prompt-limit branch.
- The controller is single-flight:
  - resolve pending order first,
  - read Binance hedge position as truth,
  - calculate `full_target`,
  - stage/reconcile to `eff_target`,
  - submit at most one hedge order for `eff_target - current`.
- HARD goes straight to full target and bypasses SOFT persistence/add cooldown/SOFT slippage guard. Cost/slippage alerts do not block HARD.
- SOFT starts at `HEDGE_SOFT_INITIAL_RATIO = 0.50`, escalates after persistence or worsening, and supports reduce hysteresis plus add/reduce cooldowns.
- Short-flat/orphan/reverse hedge states reduce-only unwind to zero before any reopen.
- Binance order lifecycle helpers were split out:
  - `bnc_submit_hedge_order`
  - `bnc_get_hedge_order`
  - `bnc_cancel_hedge_order`
- Pending hedge orders now distinguish active partial fills from terminal fills:
  active partial fills keep the pending order in single-flight state, stale
  residuals must cancel before clearing, and resolved fills are mirrored into
  snapshot `hedge_execution_history`.
- `POSITION_MANAGE` now surfaces controller state/reason, full/eff/current/delta, pending order id, cross bps, cooldowns, persistence, and episode cost warnings.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, or revoke runtime commands were added.
- Ordinary 80% TP still has the last-3h DTE gate; risk exit and hedge are not blocked by that gate.
- `LogStatus` remains the primary trader screen; ordinary `POSITION_MANAGE` cycles do not spam `Log`.
- Missing Binance position/PnL/depth data is not rendered as zero.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_4.py
```

## Final SHA256 Set

All four bundle files match:

```text
AD586FA029B6B5D8DA50D05F48A2F3CFE1D330EA49CD41BBD8240312E973B0DA  realsrc/spm_manual_gate_execution_fmz.py
AD586FA029B6B5D8DA50D05F48A2F3CFE1D330EA49CD41BBD8240312E973B0DA  artifacts/spm_manual_gate_execution_fmz.py
AD586FA029B6B5D8DA50D05F48A2F3CFE1D330EA49CD41BBD8240312E973B0DA  artifacts/spm_manual_gate_execution_fmz_v3_1_4.py
AD586FA029B6B5D8DA50D05F48A2F3CFE1D330EA49CD41BBD8240312E973B0DA  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_4.py
```

## Next Best Small Checks

- Review real FMZ Binance order-status shapes against `PENDING_ACTIVE`, `PENDING_PARTIAL_ACTIVE`, `PENDING_FILLED`, and stale recovery reason codes.
- After live logs arrive, tune SOFT persistence/cooldown values before considering maker-first or segmented execution changes.
