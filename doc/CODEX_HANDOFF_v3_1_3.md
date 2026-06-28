# CODEX HANDOFF v3.1.3

## Current Delivery

- Current version: `3.1.3-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_3.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `336A9BAE56E39A2C8F63B84C6D08EBCEE2CC605017314287AB4C6AB8656ECC5A`

## Scope

v3.1.3 is a small take-profit gate patch on top of v3.1.2. It keeps the 80%
capture take-profit idea, but avoids actively buying back ordinary profit
inside the final delivery window for the short-dated 24h / 48h workflow.

The runtime interaction boundary is unchanged: only plan confirmation codes
can trigger a runtime strategy action. Position management remains
non-interactive.

## Behavioral Change

- Added `TAKE_PROFIT_MIN_DTE_HOURS = 3.0`.
- Ordinary take-profit now requires:

```text
capture >= 80% AND remaining_short_leg_dte_hours > 3h
```

- If capture is at or above 80% but remaining DTE is `<= 3h`, ordinary TP is
  paused and the position tends toward settlement.
- This does not limit risk exit, hedge fallback, orphan hedge cleanup,
  recovery, or settlement.
- `POSITION_MANAGE` shows the final-window gate in `止盈/退出预算`, including
  the remaining DTE, configured threshold, and reason code.

## Regression Coverage Added

- Final 2h, capture above 80%, normal risk: no short-leg buyback is submitted.
- Final 2h, capture above 80%, deteriorated risk: risk exit may still fail over
  to hedge when risk exit is not executable.
- Existing v3.1.2 tests for order safety, risk-exit depth, Binance tick
  rounding/PnL, event-only `Log`, and confirmation-only runtime commands remain
  covered.

## Verification

Fresh local verification for this delivery:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_3.py
```

Expected final results:

- `281 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched
  `336A9BAE56E39A2C8F63B84C6D08EBCEE2CC605017314287AB4C6AB8656ECC5A`
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_1_3.py`

## FMZ Retest Focus

After replacing the FMZ code with v3.1.3:

- In the final 3h before short-leg expiry, confirm `POSITION_MANAGE` shows the
  ordinary-TP DTE gate when capture is already above 80%.
- Confirm ordinary 80% TP does not submit a short-leg buyback inside that
  final 3h window when risk is normal.
- Confirm risk exit / hedge can still trigger inside the same final 3h window
  when risk state deteriorates.
- Confirm the v3.1.2 fixes still hold: no routine `POSITION_MANAGE` `Log`
  spam, Binance BTCUSDC precision errors do not recur from raw prompt-limit
  floats, and risk-exit depth is shown instead of misleading zeroes.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
