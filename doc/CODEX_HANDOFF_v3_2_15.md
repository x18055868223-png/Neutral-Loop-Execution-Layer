# Codex Handoff v3.2.15

## Release

- Version: `3.2.15-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_15.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_15.py`
- SHA256:
  `6FFD8785F39148EF28E67BCBFB23B6D2DA6C56F71366E6B8DA55B5DEE0EDC4AB`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- `POSITION_MANAGE` V32 episode-cost display now labels the field as
  `reserved_not_computed` telemetry. It no longer displays `cost_bps`, avoiding
  the false impression that realized cumulative slippage/fees have been
  computed.
- `_post_taker_once()` now uses taker-specific tick rounding:
  buy taker prices round up to cross, sell taker prices round down. Existing
  maker buy rounding remains passive/downward.

## Tests Added First

- `test_position_manage_marks_episode_cost_as_reserved_not_computed`
  failed before the display change because the risk/hedge table showed
  `cost_bps` and lacked `reserved_not_computed`.
- `test_entry_protection_taker_buy_rounds_up_to_cross_ask_tick`
  failed before the execution change because a buy taker price of `0.00095`
  with `tick_size=0.0001` rounded down to `0.0009` instead of up to `0.0010`.

## Verification

- Targeted red tests reproduced both gaps before implementation.
- Targeted tests passed after implementation.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `353 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> syntax compile passed; bundle smoke passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_15.py`
  -> passed.

## Current TODO State

- `doc/OPEN_GAPS_TODO.md` shows no open must-fix or cleanup candidate after
  v3.2.15.
- Runtime interaction remains confirmation-code-only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
