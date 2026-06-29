# Live Readiness Audit Report

## Executive Summary

- Audited artifact: `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`
- Strategy version: `v1`
- SHA256: `D41E00A122023455FD75E60F2C2A29B7F23B368CCE5C60364674D6EF45ED57FC`
- Scope: FMZ Deribit S:PM manual-gate vertical credit spread execution layer,
  including manual decision intake, plan display, confirmation-code lock,
  precommit, protected entry, position management, TP/risk-exit, V32 Binance
  hedge, settlement, accounting, archive, recovery, and operator UX.

## Final Verdict

`SMALL_SIZE_LIVE_TEST_READY`

This means the current local source and generated FMZ artifact pass the
repository audit gates for a small-size live test with the configured live-test
surface. It does **not** mean FMZ live has passed. Live acceptance still requires
the trader to deploy this exact artifact, verify FMZ command configuration,
observe startup/read-only checks, and confirm exchange state and first-cycle logs.

The Opus 4.8 follow-up audit identified one P1 display gap in v3.2.26: some
reachable V32 hedge controller reasons could appear as raw machine codes in the
primary `POSITION_MANAGE` read screen. v3.2.27 verifies and closes that gap with
Chinese-first reason mappings and regression tests. v3.2.28 also closes the
Opus P2 note that exit-campaign states could appear raw in secondary read-screen
rows. No unresolved P0 or P1 issue is currently identified. Remaining risk is
operational/runtime risk outside the local deterministic harness: FMZ
environment behavior, live exchange latency, real order lifecycle edge cases,
and operator deployment/configuration mistakes.

The v1 live-validation alignment keeps the v3.2.28 safety skeleton and narrows
only the real-fill entry parameters: protection maker fallback is now 60 seconds
instead of 600 seconds, short-leg maker wait is now 15 seconds, and the operator
status line shows fallback elapsed/threshold/remaining state.

## Evidence Baseline

| Evidence | Result |
|---|---|
| `realsrc/tests/run_all.py` | `403 passed, 0 failed` |
| lifecycle matrix + live-default version tests | `47 passed, 0 failed` |
| `realsrc/build_bundle.py --check` | syntax compile and bundle smoke passed |
| latest delivery `py_compile` | passed |
| `artifacts/最新交付/` | exactly one current file: `spm_manual_gate_execution_fmz_v1.py` |
| bundle hash sync | source/generated/generic/versioned/latest all share the same SHA256 |

These are local verification artifacts only.

## Severity Table

| Severity | Final State | Evidence |
|---|---|---|
| P0 | No open P0 found | TEST no-order rows 001/003-006/014; protected-entry rows 010-015; false-settlement rows 035/039; orphan cleanup rows 006/031-033/040; archive/accounting rows 037/038/041; full suite green. |
| P1 | No open P1 found | Precommit, budget, V32 hedge, settlement accounting, recovery, and Chinese-first display covered by unit tests plus the 41-row matrix. The Opus-found V32 reason leak is closed by `test_v32_policy_reasons_are_chinese_mapped` and the crash read-screen assertion. |
| P2 | No blocking P2 | The Opus exit-campaign raw-state display note is closed in v3.2.28. Remaining caveats are documentation/runtime acceptance limits rather than code defects: no FMZ live proof, no guarantee against exchange-specific latency beyond fail-closed/pending-first rules. |

## Lifecycle Audit

| Stage | Result | Evidence |
|---|---|---|
| Manual decision | Pass | Manual context lineage and validation tests; plan menu remains bound to current context/version. |
| FMZ boot | Pass locally | Startup self-check is read-only and surfaced in status; live FMZ boot still requires operator observation. |
| Startup recovery | Pass | Recovery tests plus matrix rows 031-034 prove manual cleanup/read-failure behavior and state-drift recovery. |
| Plan menu | Pass | Plan rows 001-002, command rows 007-009/014, and candidate/menu tests cover display, lockability, stale/version binding. |
| Confirmation code | Pass | Runtime command router accepts only `执行:<code>`, `EXECUTE:<code>`, or bare code; legacy commands route to UNKNOWN. |
| Precommit | Pass | Unknown same-leg orders, budget gaps, stale lineage, VRP/context gaps, and execution feasibility fail closed. |
| Protected entry | Pass | Rows 010-015 prove protection-first entry, no naked short, no duplicate maker order, and late fill idempotency. |
| Snapshot freeze | Pass | Full/partial/protection-only entry progress moves to safe managed snapshots or keeps the locked plan. |
| Position management | Pass | Position display tables and matrix rows cover normal holding, TP/risk, hedge, settlement, and recovery states. |
| TP / risk exit | Pass | Rows 016-023 prove budget cap, ask-depth requirement, quote/depth gaps, idempotency, and no overspend. |
| V32 hedge | Pass | Rows 024-030 and hedge-policy tests prove pending-first, missing-order-id guard, SOFT/HARD/final-3h/reduce semantics. v3.2.27 additionally verifies all reachable V32 policy reasons have Chinese-first display mappings. |
| Settlement reconcile | Pass | Rows 035-040 and settlement tests prove strict read failure, idempotent settlement, DATA_GAP accounting, and hedge cleanup before archive. |
| Protection recovery | Pass | Unit tests prove net recovery value/fees accounting; row 041 proves repeated `run_cycle()` does not duplicate recovery sale/accounting/archive; TEST rows prove no recovery order in TEST. |
| Orphan hedge cleanup | Pass | Auto cleanup only under strict safe evidence in LIVE; TEST dry-run; read/unknown-order failures remain manual. |
| Closed archive | Pass | Archive tests and rows 037-038 prove closed-history creation, no duplicate archive, and stale recovery cleanup when safe. |

## Scenario Matrix Result

All 41 numbered lifecycle rows in `TEST_SUMMARY.md` pass. The matrix verifies
state, order/no-order evidence, ledger mutation, and status text for the covered
states. v3.2.27 adds display-registry coverage for the V32 hedge reasons outside
the numbered matrix; v3.2.28 adds display-registry coverage for exit-campaign
states.

| Range | Coverage |
|---|---|
| 001-006 | TEST no real orders, plan-phase no-order status, no-order TP/recovery/hedge/orphan cleanup. |
| 007-009, 014 | Confirmation code lock/reject/dry behavior and precommit unknown-order blocking. |
| 010-015 | Protected entry, protection-only progress, partial vertical, pending maker order, late fill idempotency. |
| 016-023 | TP/risk-exit cap/depth/quote blockers and repeated-loop fill accounting. |
| 024-030 | V32 hedge pending, missing order ID, terminal fill, SOFT/HARD/final-3h/reduce display and orders. |
| 031-034 | Startup orphan manual cleanup, Binance/Deribit read failure screens, lost state recovery. |
| 035-040 | Settlement false-read prevention, settlement idempotency, archive, DATA_GAP final PnL, and settlement-with-perp reduce-only cleanup. |
| 041 | Protection recovery fill repeated-loop no-double-count behavior. |

## Recovery Decision Table

| State | Evidence Required | allow_new_open | auto_cleanup_allowed | real order allowed? | Operator Message | Expected Display |
|---|---|---:|---:|---:|---|---|
| clean no position | no snapshot, no exchange option/perp risk, no unknown orders | yes | no | no | clean / plan allowed | plan phase tables |
| valid locked plan | current menu/version/context, valid unexpired confirmation code | no until entry completes or lock clears | no | entry only if precommit and gate pass | plan locked / precommit | locked-plan console and precommit rows |
| protection-only progress | filled protection, no short fill | no | no | continue selected entry campaign only | no naked short formed | protection progress row |
| partial vertical | short qty <= protection qty, entry progress adopted | no | no | risk-reducing actions only | partial vertical managed | position-manage tables |
| full vertical | snapshot exists and reconciles | no | no | exits/hedges by gates | holding / monitoring | position summary, TP/risk, hedge, ledger |
| exit in progress | pending or recent exit order/fill | no | no | no duplicate exit; resolve pending first | active order/pending | active order and TP/risk rows |
| hedge pending | V32 pending order state exists | no | no | no new hedge until pending resolves | pending hedge | hedge pending reason in Chinese |
| option read failure | Deribit option position query failed | no | no | no settlement mutation | manual check Deribit positions | recovery/data-gap wording |
| Binance read failure | Binance hedge position query failed | no | no | no orphan cleanup | manual check Binance hedge | recovery/data-gap wording |
| no option short + perp + clean evidence | no option short, Binance perp, successful option/open-order/Binance reads, no unknown orders, order lifecycle supported | no until cleanup complete | LIVE yes / TEST dry only | reduce-only cleanup only | automatic reduce-only cleanup | orphan auto-cleanup phase |
| no option short + perp + unknown orders | no option short and perp, but unknown active order exists | no | no | no | manual only-reduce cleanup required | orphan manual-cleanup phase |
| both option legs settled + no perp | both legs absent after grace, settlement computed or DATA_GAP, no hedge pending | yes after archive | no | no | closed and archived | closed/archive ledger |
| both option legs settled + perp remains | both legs settled, Binance perp nonzero | no | yes if safe | reduce-only hedge cleanup only | cleanup before archive | settlement + hedge cleanup rows |

## Accounting Audit

The ledger separates:

- entry credit: short credit minus protection cost and entry fees;
- exit spend: short buyback spend and fees;
- protection recovery: sale proceeds minus recovery fees;
- settlement cashflow: explicit signed settlement-currency value;
- option realized/final PnL: entry, exit, recovery, and settlement only;
- hedge telemetry/PnL: kept separate from option PnL unless explicitly named;
- status: `COMPUTED`, `ESTIMATED`, `DATA_GAP`, or open/not computed.

Rows 035-041 and settlement/recovery unit tests verify that missing settlement
price is not rendered as a fake zero and that repeated settlement, archive,
exit, hedge, and protection-recovery loops do not double count.

## Operator Runbook

1. Deploy only `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`.
2. In FMZ, configure `GetCommand()` command name as `执行` with type `string`.
3. Confirm the editable live-test block before start:
   `RUN_PROFILE`, `DIRECTION_BIAS`, `ORDER_AMOUNT`, `RISK_EXIT_MAX_SPEND`,
   and action gates.
4. On boot, read `LogStatus` first. Treat `Log` as event/exception stream.
5. Do not enter any command except the displayed confirmation code.
6. If the panel shows data gap, unknown active order, or manual cleanup, verify
   Deribit option positions, open orders, and Binance perp manually before
   taking external action.
7. For the first live test, use the configured small size only and watch the
   first protection-leg order, short-leg order, hedge state, and ledger rows.
8. Do not treat local green tests as FMZ live proof; save FMZ logs and exchange
   screenshots/state snapshots for the first real acceptance pass.

## Remaining Risks And Limits

- No local test can prove FMZ live command wiring, exchange network behavior, or
  real exchange fill/cancel latency.
- The strategy is ready for a small live test with explicit monitoring, not for
  unattended large-size operation.
- If FMZ reports missing Python features or unexpected exchange API return
  shapes, treat it as a live acceptance failure and stop new entry until patched.

## Conclusion

The local audit found no unresolved P0/P1 blockers. The artifact is suitable for
small-size live-test deployment under the runbook above, with FMZ/exchange live
acceptance still pending.
