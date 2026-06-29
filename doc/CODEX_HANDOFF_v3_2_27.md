# Codex Handoff v3.2.27

## Release

- Version: `3.2.27-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_27.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_27.py`
- SHA256:
  `A6EC0448C69FBFF9309739AE63A01CF2A1AA16218A8D1BD1856341F51B2BDA0C`
- Boundary: local verification only. This is not FMZ live proof.

## Opus Finding

Opus 4.8 reported one verified P1 UX gap in v3.2.26: reachable V32 hedge
controller reasons could appear as raw machine codes in the primary
`POSITION_MANAGE` read screen, for example `CRASH_TRIGGER_SPEED`,
`LOT_DEADBAND`, `SOFT_TRIGGER_CONFIRMED`, and `HOLD_EXISTING`.

This was confirmed against both source and the v3.2.26 latest delivery. It was
not a source/bundle drift issue.

## Changes

- Added Chinese-first `REASON_CN` mappings for the remaining reachable V32 hedge
  policy reasons, including policy-disabled, Binance position-read failure,
  target data gap, SOFT confirmed, crash speed trigger, cooldown/min-hold,
  hysteresis wait, reverse unwind, steady hold/no-trigger, and deadband states.
- Kept the implementation to the existing display mapping table. No new display
  compatibility layer, no hedge decision change, and no order lifecycle change.
- Updated version and delivery metadata from v3.2.26 to v3.2.27.

## Tests Added First

- `test_v32_policy_reasons_are_chinese_mapped` enumerates reachable V32 policy
  reasons and fails if any maps to itself or includes the raw code.
- The crash observability display test now asserts `CRASH_TRIGGER_SPEED` is not
  emitted into the status panel and the Chinese crash reason is present.
- Initial RED evidence:
  `test_v32_policy_reasons_are_chinese_mapped` failed first on
  `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT` returning raw.

## Verification

- Targeted display + live-default tests:
  `27 passed, 0 failed`
- Full local suite:
  `398 passed, 0 failed`
- Lifecycle matrix + live-default version tests:
  `47 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_27.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_27.py` after removing py_compile cache.
- Source/generated/generic/versioned/latest bundle hashes all match:
  `A6EC0448C69FBFF9309739AE63A01CF2A1AA16218A8D1BD1856341F51B2BDA0C`.

## Remaining Work

- No open local P0/P1 is currently identified after the Opus P1 fix.
- FMZ live acceptance remains pending and must use the exact v3.2.27 artifact,
  saved FMZ logs, and exchange state snapshots. Local green tests are still not
  FMZ live proof.
