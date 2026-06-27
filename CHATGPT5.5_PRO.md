# GPT-5.5 Pro Handoff: Neutral Loop Execution Layer

## Current State

This repo is the standalone FMZ execution-layer handoff for
`spm_manual_gate_execution_fmz.py`. The current deliverable is
`STRATEGY_VERSION = "3.0.13-manual-gate"`.

Editable source lives in `realsrc/src/`. Tests live in `realsrc/tests/`.
The FMZ single-file bundle is built by `realsrc/build_bundle.py`.

Delivery convention:

- Versioned backups stay in `artifacts/`.
- `artifacts/最新交付/` contains exactly one current versioned FMZ file.
- Do not hand-edit generated artifacts; edit `realsrc/src/`, then rebuild.

## Ponytail Rule

Default future work is ponytail/full: reuse first, standard library second,
minimum new code last. Delete stale paths instead of preserving compatibility
that the operator will not use.

Do not add speculative adapters, old-mode bridges, hidden fallback inputs, or
unused strategy phases. If a compatibility path is not part of the current FMZ
workflow, remove it precisely and cover the deletion with a focused test.

## Operator Configuration

The top config block is now live-test oriented by default. The operator should
normally only edit the core live fields:

- `ROBOT_ID`
- `DIRECTION_BIAS`
- `ORDER_AMOUNT`
- `SHORT_DELTA_RANGE`
- `PROTECTION_WIDTH_RANGE`
- `RISK_EXIT_MAX_SPEND`
- `ALLOW_ENTRY_TRADING`
- `ALLOW_EXIT_TRADING`
- `ALLOW_HEDGE_TRADING`
- `KILL_NEW_RISK`
- `EMERGENCY_REDUCE_ONLY`
- `HEDGE_VENUE`
- `HEDGE_BINANCE_INSTRUMENT`
- `HEDGE_BINANCE_MIN_TRADE`
- `HEDGE_BINANCE_EXCHANGE_INDEX`
- `GEX_CONTEXT_API_BASE`
- `GEX_CONTEXT_API_KEY`

Default small-live-test posture:

- `RUN_PROFILE = "LIVE"`
- `DRY_RUN_PASSED = True`
- `ALLOW_ENTRY_TRADING = True`
- `ALLOW_EXIT_TRADING = True`
- `ALLOW_HEDGE_TRADING = True`
- `RISK_EXIT_MAX_SPEND = 0.001`
- Binance hedge venue is the default; Deribit perpetual remains compatibility
  only.

Legacy operator inputs for audit-card references, manual notes, plan/order
rounds, selected preview plans, the old global trading switch, and the old
kill switch have been removed. Do not reintroduce them.

## Planning Rule

The candidate library is centered on near-24h capital efficiency:

- Internal target DTE is 24 hours.
- The planner selects the expiry nearest to 24h, then the next later exchange
  expiry if available.
- At most two expiries enter the candidate library.
- Thin premium and low margin relief are warnings/scoring inputs, not hard
  blockers for these short-dated candidates.

Hard fail-closed checks still apply to real execution:

- valid option quotes,
- spread/liquidity sanity,
- positive executable net credit,
- portfolio budget,
- risk-exit budget,
- order recovery and ledger checks.

## Main Path

`manual live config -> Deribit option-chain -> nearest-24h vertical candidates
-> S:PM / execution feasibility / VRP validity / budget filters -> confirm code
-> precommit -> entry campaign -> position management -> exit / hedge / recovery`

Existing positions continue through management, exit, hedge, orphan cleanup, and
recovery even if new planning is disabled.

## Verification

Windows / Python 3.12:

```powershell
$py = 'C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe'

& $py realsrc\tests\run_all.py
& $py realsrc\build_bundle.py --check
& $py -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_13.py

# Run the v3.0.13 legacy-config scan listed in
# realsrc\tests\test_v3_0_13_live_24h.py against source and current delivery.
```

Expected:

- all tests pass,
- build check passes,
- py_compile passes,
- the exact legacy config scan has no hits in source or current delivery,
- `artifacts/最新交付/` contains only the current versioned file.

## Guardrails

Do not treat local tests or bundle compilation as FMZ live proof. Live readiness
comes from the user's FMZ run logs and exchange state. Keep planning, entry,
hedge, exit, recovery, and ledger concerns separated; do not let a hedge change
candidate selection or precommit behavior.
