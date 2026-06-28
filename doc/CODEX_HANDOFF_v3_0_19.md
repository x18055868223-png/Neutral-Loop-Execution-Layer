# CODEX HANDOFF v3.0.19

## Current Delivery

- Current version: `3.0.19-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_19.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `22A5908B6705883711B66D06D436AA23DEFB45C737C50AC0EBC1B63D86118D70`

## Root Cause

v3.0.18 restored the near-24h `28JUN26` expiry, but only one 28JUN26 short strike appeared. The remaining bottleneck was the normal protection width rule:

- Regular config stayed at `PROTECTION_WIDTH_RANGE = (2000, 2500)`.
- Expiry-day protection legs are often very cheap and sparse.
- A valid short such as `59500-P` can need a `1500`-wide protection leg to form a buildable vertical.
- `_build_menu()` also kept only one protection leg per short leg, which limited expiry-day diversity.

## Fix

1. Added endgame-expiry config:
   - `ENDGAME_DTE_HOURS = 24`
   - `ENDGAME_PROTECTION_WIDTH_MIN = 1500`
   - `ENDGAME_PROTECTION_CHOICES_PER_SHORT = 2`
2. Near-24h candidates now use `1500..PROTECTION_WIDTH_RANGE[1]` as the active protection width range.
3. Near-24h candidates keep up to two protection choices per qualified short leg; later expiries still keep one protection leg and use the regular width range.
4. Bumped `STRATEGY_VERSION` to `3.0.19-manual-gate`.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_19.py
```

Results:

- `252 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched `22A5908B6705883711B66D06D436AA23DEFB45C737C50AC0EBC1B63D86118D70`

Regression coverage updated:

- `test_menu_keeps_20h_put_when_low_premium_protection_is_buyable` now requires at least two near-20h put candidates, includes short strikes `59500` and `60000`, and verifies a `1500` width candidate exists.

## FMZ Retest Focus

After replacing the FMZ code with v3.0.19, the fixed candidate library should show more expiry-day diversity when the live chain supports it: typically 2-4 near-24h candidates across eligible short strikes and protection widths. `60500` should still be filtered if its delta is outside the configured `SHORT_DELTA_RANGE`; this change relaxes protection-leg width, not the short-delta risk envelope.
