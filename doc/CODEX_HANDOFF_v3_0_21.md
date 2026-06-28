# CODEX HANDOFF v3.0.21

## Current Delivery

- Current version: `3.0.21-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_21.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `D35B0782EAB4D88577DCC926E6D745A1A0B7DBF3FBB272BB5586C6FAC1671F5F`

## Root Cause

In live testing, the protection leg was still behaving like a short-cycle
maker attempt: place, wait a few seconds, cancel, then place again. For very
short-dated low-premium protection legs this churn is worse than simply keeping
the order resting at the mark-derived price, because the protection leg is cheap
and liquidity is thin.

The prior taker fallback was also tied to attempt count and a one-tick ask
restriction. The desired live boundary is time-based: after 10 minutes from the
first protection maker order, the robot may take best ask if size and net-credit
safety gates pass.

## Fix

1. Entry progress now stores `entry.prot_order` with `order_id`, `instrument`,
   `price`, `amount`, `filled_seen`, `placed_ms`, `wait_start_ms`, and `label`.
2. Each `run_cycle` queries the existing protection order state instead of
   sleeping and cancelling it.
3. Protection maker target is the current mark rounded in the buy direction; if
   mark touches/crosses best ask, the target is capped at `best_ask - tick`.
4. The protection maker is cancelled and replaced only when the target changes
   by at least one tick. Repricing does not reset `wait_start_ms`.
5. If order-state lookup fails, the strategy keeps the locked plan and existing
   `prot_order`, does not place a duplicate order, and surfaces
   `PROTECTION_ORDER_STATE_UNKNOWN`.
6. `ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600` replaces the old attempt-based
   protection fallback.
7. After 10 minutes, the robot cancels the maker, checks late fill, and may buy
   best ask without the old one-tick restriction only when ask depth covers the
   remaining quantity and projected net credit stays above
   `ENTRY_MIN_NET_CREDIT`.
8. If depth or net credit fails, the robot continues the mark maker path and
   keeps the selected plan locked.
9. Short leg behavior stays v3.0.20: wait for protection fill first, then use
   post-only maker with a 60-second rest.
10. Locked-plan status now includes the current protection order id, price,
    elapsed wait time, and whether it has entered the taker fallback zone.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_21.py
```

Results:

- `265 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched `D35B0782EAB4D88577DCC926E6D745A1A0B7DBF3FBB272BB5586C6FAC1671F5F`
- `artifacts/最新交付/` contains only `spm_manual_gate_execution_fmz_v3_0_21.py`

Regression coverage updated:

- First protection maker order persists without `Sleep()` or immediate cancel.
- Unchanged mark target reuses the same `order_id` with no duplicate order.
- A one-tick mark target change cancels, checks late fill, and re-posts while
  preserving `wait_start_ms`.
- Ten-minute fallback takes best ask only when depth and net credit pass.
- Ten-minute fallback keeps mark maker when depth or net credit fails.
- Partial fills across cycles count only newly observed fill.
- `_attempt_commit()` writes `prot_order` back to `_LOCKED_KEY` while staying in
  `PLAN_LOCKED`.
- Startup recovery still cancels entry-labeled unfinished orders before
  rebuilding state from real exchange positions.

## FMZ Retest Focus

After replacing the FMZ code with v3.0.21:

- Confirm a near-24h plan and verify the protection leg remains as one resting
  maker order instead of being cancelled every few seconds.
- If mark-derived target price changes, verify only then the old protection
  maker is replaced and the displayed wait time continues from the original
  first placement.
- If the protection leg is still unfilled after 10 minutes, verify taker only
  happens when best ask depth covers the remaining amount and net credit remains
  valid.
- Confirm no new candidate library is pushed while the selected plan is in
  entry campaign.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
