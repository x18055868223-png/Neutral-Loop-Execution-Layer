# Formal v1 Seal Audit

Date: 2026-06-29

## Conclusion

`v1` is the formal live-validation version based on the final test-round
artifact plus the real-fill order-parameter adjustment.

The lineage is:

`v3.2.28-manual-gate` test-round final safety skeleton
-> public Deribit fill-scenario audit
-> v1 order-parameter alignment
-> formal live-validation bundle.

No local evidence suggests that v1 is a rewrite or a behavior reset. The
changes are intentionally narrow: version label, protection-leg fallback
timing, short-leg maker wait, status-line wait-budget visibility, generated
bundle headers, and release documentation.

## Field Residue Audit

Result: pass.

- Current source declares `STRATEGY_VERSION = "v1"`.
- Current source keeps protection fallback at `60` seconds and short-leg maker
  wait at `15` seconds.
- Current generated/source/generic/latest bundles share the same SHA256:
  `D41E00A122023455FD75E60F2C2A29B7F23B368CCE5C60364674D6EF45ED57FC`.
- The latest-delivery directory contains only
  `spm_manual_gate_execution_fmz_v1.py`.
- No `3.2.28-manual-gate` strategy version residue exists in the v1 source,
  generated source bundle, generic artifact, versioned v1 artifact, or latest
  delivery artifact.
- `PLAN`, `ORDER`, `APPROVE_PLANNING`, and `REJECT` matches were reviewed as
  valid internal planning/status/feasibility terms, not leftover runtime
  operator commands.
- Runtime command intake remains confirmation-code-only through
  `执行:<code>`, `EXECUTE:<code>`, or bare confirmation code; legacy action
  words route to unknown/ignored behavior.

## Logic Review

Result: pass with live-acceptance boundary.

- Protected entry remains protection-first. The short leg is still blocked
  until protection fill coverage exists.
- Protection maker order remains persistent and mark-derived. The taker
  fallback clock is non-resetting and now reaches the controlled fallback zone
  after 60 seconds.
- The 60-second taker fallback does not bypass the safety checks: visible ask
  depth must cover the remaining protection amount and the net-credit floor
  must still pass.
- The short leg remains maker-first with a 15-second wait, matching the
  real-fill audit's conclusion that the seller leg has better liquidity and
  should not wait as long as the protection leg.
- Existing fail-closed paths remain in place: unknown active orders, data gaps,
  order-state uncertainty, missing order IDs, hedge pending orders, and TEST
  profile no-real-order behavior.
- Status display now exposes elapsed/threshold/remaining protection wait so
  the operator can see why the execution layer is still waiting or has entered
  the fallback zone.

## Version Classification

- `v1` is the only formal live-validation release.
- All `v3*` generated bundles are test-round archives.
- The previous latest-delivery `spm_manual_gate_execution_fmz_v3_2_28.py` has
  been removed from `artifacts/最新交付/`; v3.2.28 remains only as a historical
  test-round archive in `artifacts/`.

## Verification Evidence

- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `403 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> syntax compile passed and bundle smoke passed
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v1.py`
  -> passed

Boundary: this is local seal evidence only, not FMZ live proof.
