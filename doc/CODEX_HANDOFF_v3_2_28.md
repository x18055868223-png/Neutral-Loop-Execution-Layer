# Codex Handoff v3.2.28

## Release

- Version: `3.2.28-manual-gate`
- Release class: test-round archive, superseded by formal `v1`.
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_28.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_28.py`
- SHA256:
  `A29EA7AB388AEF2B154BE850A9B4774E3FEFF7FDDFA34327F79FF0939BE308B6`
- Boundary: local verification only. This is not FMZ live proof.

## Opus Finding

After closing the v3.2.27 P1 hedge-reason display leak, the remaining verified
Opus display note was P2-C: `exit_campaign_state` values such as `WORKING_LONG`,
`LONG_RESIDUAL_ONLY`, and `PAUSED_BY_BUDGET` could appear raw in secondary
operator rows.

P2-B was reviewed but not changed: Opus classified it as not a current defect,
and adding another `allow_live` guard would duplicate the existing TEST gate
behavior without closing a demonstrated route to live orders.

## Changes

- Added `EXIT_CAMPAIGN_STATE_CN` and `disp_exit_campaign_state_cn()`.
- Routed lifecycle notes, pipeline exit-module rows, and console exit-activity
  rows through the same display mapping.
- Kept the change display-only: no exit decision, order, gate, or accounting
  behavior changed.

## Tests Added First

- `test_exit_campaign_states_are_chinese_mapped` verifies all reachable
  exit-campaign states map to Chinese text.
- `test_position_manage_exit_campaign_state_is_chinese_first` verifies
  `WORKING_LONG` does not leak into the `POSITION_MANAGE` status panel.
- `test_long_recovery_hint_does_not_expose_raw_exit_state` verifies the
  protection-recovery operation hint does not mention `LONG_RESIDUAL_ONLY`.
- Initial RED evidence:
  `test_exit_campaign_states_are_chinese_mapped` failed with
  `AttributeError: module 'display' has no attribute 'disp_exit_campaign_state_cn'`.

## Verification

- Targeted display + live-default tests:
  `30 passed, 0 failed`
- Full local suite:
  `401 passed, 0 failed`
- Lifecycle matrix + live-default version tests:
  `47 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_28.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_28.py` after removing py_compile cache.
- Source/generated/generic/versioned/latest bundle hashes all match:
  `A29EA7AB388AEF2B154BE850A9B4774E3FEFF7FDDFA34327F79FF0939BE308B6`.

## Remaining Work

- No open local P0/P1 is currently identified after the Opus follow-up fixes.
- No open cleanup candidate is currently identified from the Opus feedback.
- This artifact is now classified as a test-round archive. Formal live
  validation should use the v1 latest-delivery artifact instead, with saved FMZ
  logs and exchange state snapshots. Local green tests are still not FMZ live
  proof.
