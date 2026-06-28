# CODEX HANDOFF v3.0.18

## Current Delivery

- Repository: `ex18055868223-png/Neutral-Loop-Execution-Layer`
- Local path: `C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`
- Current version: `3.0.18-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_18.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `B39A9F60B24C620266D87431939A0DD125E9D731C0BA982C89897EC3D22A0AC2`

## Root Cause

The v3.0.17 confirmation-code display fix worked, but the candidate library still showed only 1.9d `29JUN26` plans while `28JUN26` had about 20h remaining.

Fresh Deribit public read-only checks confirmed `28JUN26` BTC puts existed. Representative quotes at the time:

- `BTC-28JUN26-60000-P`: bid/ask about `0.0021/0.0025`, delta about `-0.33`
- `BTC-28JUN26-58000-P`: bid/ask about `0.0001/0.0003`

The near-24h short leg was executable, but the low-premium protection leg had a very wide relative spread. The old execution-feasibility gate allowed only `PROTECTION_ABS_SPREAD_MAX = 0.00015`, so a two-tick low-premium protection leg with absolute spread `0.0002` was rejected and the 20h candidate disappeared.

There was also a persistence issue: the fixed FMZ candidate-library cache was validated only by manual context/config signature, not by strategy version. A v3.0.17 robot could keep showing a previously frozen menu after an upgrade.

## Fix

1. Raised `PROTECTION_ABS_SPREAD_MAX` from `0.00015` to `0.00025` so buyable low-premium protection legs with small absolute spread can pass the soft low-premium protection-spread path.
2. Added `strategy_version` to stable menu metadata and required it in `_stable_menu_meta_valid()`. Missing or old-version stable menus are cleared and rebuilt.
3. Bumped `STRATEGY_VERSION` to `3.0.18-manual-gate`.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_18.py
```

Results:

- `252 passed, 0 failed`
- bundle build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched `B39A9F60B24C620266D87431939A0DD125E9D731C0BA982C89897EC3D22A0AC2`

New regression coverage:

- `test_near_expiry_low_premium_protection_two_tick_spread_is_softened`
- `test_menu_keeps_20h_put_when_low_premium_protection_is_buyable`
- `test_stable_menu_meta_requires_current_strategy_version`

## FMZ Retest Focus

After replacing the FMZ code with v3.0.18, the first rebuilt candidate library should no longer reuse the v3.0.17 frozen rows. If Deribit still has the 28JUN26 near-24h put vertical with executable short bid and buyable protection ask, the fixed candidate library should include the 20h expiry rather than only 1.9d plans.
