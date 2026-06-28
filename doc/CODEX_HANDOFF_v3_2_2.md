# CODEX HANDOFF v3.2.2

## Current Delivery

- Version: `3.2.2-manual-gate`
- Current FMZ file: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_2.py`
- Bundle SHA256: `F1A1B408BE8E1F401E4CA6FEADB6379EFE027EDD749ED354B7B64B03978DAA88`
- Local verification: `338 passed, 0 failed`; `realsrc/build_bundle.py --check` passed; latest delivery `py_compile` passed.
- FMZ live status: not claimed. Live conclusions must come from user FMZ logs and exchange state.

## What Changed

- Binance `GetPosition() is None` now returns a data gap (`None`) instead of a flat-zero position.
- V32 hedge submit requires `GetOrder` and `CancelOrder`; exchanges without lifecycle methods return `BINANCE_ORDER_LIFECYCLE_UNSUPPORTED` before any order is sent.
- Live hedge submit responses without an order id return `BINANCE_ORDER_ID_MISSING` and set `last_submit_unknown_*` in hedge policy state.
- A recent unknown submit blocks immediate duplicate hedge submission with `SUBMIT_UNKNOWN_RECENT` until the next read-as-truth window.
- Hedge policy state now uses `spm_hedge_policy_v32_state` and migrates old `spm_hedge_policy_v313_state` once, preserving pending order state.
- `HEDGE_POLICY_V32_ENABLED` is the primary switch. Disabled policy holds with `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`; it does not fall back to legacy hedge submit.
- Minimal V32 config rejects Deribit hedge venue and rejects `HEDGE_MAKER_FIRST_REDUCE_ENABLED=True`.
- `HEDGE_SOFT_PERSIST_SECONDS` default moved from `20` to `60`.

## Guardrails Preserved

- Runtime commands remain confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- No TP authorization, risk-exit authorization, reject, stop, resume, revoke, or manual hedge runtime commands were added.
- Position management remains non-interactive; hedge/exit/TP are still config-gated and exchange-state driven.
- No maker-first reduce, ES optimizer, vol-speed filter, native conditional order, or multi-venue hedge fallback was added.
- PnL completion is not claimed. Settlement cashflow, protection recovery value, final option PnL, and real portfolio budget remain queued in `doc/OPEN_GAPS_TODO.md`.

## Verification Commands

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_2.py
```

## Final SHA256 Set

All four bundle files match:

```text
F1A1B408BE8E1F401E4CA6FEADB6379EFE027EDD749ED354B7B64B03978DAA88  realsrc/spm_manual_gate_execution_fmz.py
F1A1B408BE8E1F401E4CA6FEADB6379EFE027EDD749ED354B7B64B03978DAA88  artifacts/spm_manual_gate_execution_fmz.py
F1A1B408BE8E1F401E4CA6FEADB6379EFE027EDD749ED354B7B64B03978DAA88  artifacts/spm_manual_gate_execution_fmz_v3_2_2.py
F1A1B408BE8E1F401E4CA6FEADB6379EFE027EDD749ED354B7B64B03978DAA88  artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_2.py
```

## Next Best Small Version

- v3.2.3 should start with settlement cashflow and protection recovery accounting, with failing tests for OTM/ITM short, ITM long, both-ITM vertical, missing settlement price, and fallback-index `ESTIMATED` status.
- Keep `doc/OPEN_GAPS_TODO.md` updated before and after each small-version release.
