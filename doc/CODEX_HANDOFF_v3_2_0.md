# CODEX HANDOFF v3.2.0

## Current Delivery

- Version: `3.2.0-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_0.py`
- Bundle SHA256: `14A80AF1D2F746A5981BDD0E52811EB3AB257E85756A39C9134AAC3EB04017B5`
- Local verification: `322 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Upgraded the hedge reconciliation controller to policy label `V32`.
- SOFT hedge sizing is now gamma-aware:
  - base ratio is `HEDGE_SOFT_INITIAL_RATIO = 0.40`,
  - gamma floor is `HEDGE_GAMMA_FRAC_FLOOR = 0.30`,
  - gamma normalization reference is `HEDGE_GAMMA_NORM_REF = 1_000_000.0`,
  - SOFT uses `max(base_ratio, gamma_fraction)`, while persisted/worsened SOFT escalates to full.
- Full hedge target now represents raw 100% net option delta when gamma-aware mode is enabled; HARD and CRASH use full target directly.
- Added `HEDGE_REBALANCE_BAND_FRAC = 0.20` so small rehedges inside the target band are held instead of churning orders.
- Added ordinary reduce min-hold via `HEDGE_MIN_HOLD_SECONDS = 720`; orphan/reverse unwind paths remain allowed.
- Added final-3h SOFT-add suppression via `HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"`; HARD/CRASH/reduce/orphan handling still runs.
- Added a simple 10-minute adverse-price CRASH override with `HEDGE_CRASH_MOVE_BPS = 110`.
- Neutralized the old Deribit dry hedge-intent output from `hedge_risk`; position risk no longer emits a synthetic hedge command.
- Stabilized half-tick hedge target rounding so raw full-delta targets are not lost to floating-point tails.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, revoke, or manual hedge runtime commands were added.
- Position management remains non-interactive: TP, risk exit, and hedge are evaluated through config gates and exchange state.
- `LogStatus` remains the primary trader screen; `Log` stays event/error oriented.
- Binance hedge position read remains fail-closed; missing hedge position data is not treated as zero.
- Pending hedge single-flight, reduce-only reduce/unwind, sub-min deadband, and hedge execution history behavior are preserved.
- `HEDGE_MAKER_FIRST_REDUCE_ENABLED = False`; maker-first reduce is intentionally not delivered in v3.2.0.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_0.py
```

## Final SHA256 Set

All four bundle files match:

```text
14A80AF1D2F746A5981BDD0E52811EB3AB257E85756A39C9134AAC3EB04017B5  realsrc/spm_manual_gate_execution_fmz.py
14A80AF1D2F746A5981BDD0E52811EB3AB257E85756A39C9134AAC3EB04017B5  artifacts/spm_manual_gate_execution_fmz.py
14A80AF1D2F746A5981BDD0E52811EB3AB257E85756A39C9134AAC3EB04017B5  artifacts/spm_manual_gate_execution_fmz_v3_2_0.py
14A80AF1D2F746A5981BDD0E52811EB3AB257E85756A39C9134AAC3EB04017B5  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_0.py
```

## Next Best Checks

- Replay one user-provided FMZ hedge episode after deployment to compare SOFT add/reduce frequency before and after the 20% band.
- Review whether CRASH should use mark/index/liquid market price once live logs show the available price source quality.
- Keep maker-first reduce disabled until order-book/lifecycle evidence shows it reduces slippage without increasing stuck pending risk.
