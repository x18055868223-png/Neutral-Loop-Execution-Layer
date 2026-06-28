# CODEX HANDOFF v3.0.20

## Current Delivery

- Current version: `3.0.20-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_20.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `DA127B9F1E5CC9C93886C99D2A155F53AA56BD66968EBAA705ECE95BF76300F9`

## Root Cause

During live entry testing, a confirmed near-24h plan returned to the candidate
library after roughly the old 20-attempt entry cap. The entry cap was still
treated as a terminal abandon condition even when no option leg had filled, so
`_attempt_commit()` could clear `_LOCKED_KEY`; the next `run_cycle()` rebuilt
and displayed a fresh plan menu.

A second boundary was also too aggressive: protection-leg-only progress was
immediately adopted as a residual position, instead of continuing the selected
structure's entry campaign.

## Fix

1. `ENTRY_MAX_ATTEMPTS` is now a soft wait cap for protection-leg taker fallback,
   not a locked-plan abandon trigger.
2. No-fill and protection-only progress keep the confirmed plan locked and keep
   the same entry campaign state.
3. Protection-leg entry price now joins mark/bid without crossing the ask first.
4. After the soft wait cap, protection-leg taker is allowed only when:
   - best ask depth covers the target quantity,
   - best ask is no more than one tick above mark,
   - projected net credit still satisfies the floor.
5. Short-leg entry remains maker/post-only, but its order rest time is now
   independently configurable and defaults to 60 seconds.
6. Bumped `STRATEGY_VERSION` to `3.0.20-manual-gate`.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_20.py
```

Results:

- `255 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched `DA127B9F1E5CC9C93886C99D2A155F53AA56BD66968EBAA705ECE95BF76300F9`
- `artifacts/最新交付/` contains only `spm_manual_gate_execution_fmz_v3_0_20.py`

Regression coverage updated:

- Entry campaign decision no longer abandons locked plans on the soft attempt cap.
- `_attempt_commit()` keeps `_LOCKED_KEY` when no fills happen after the cap.
- Protection-only progress keeps the locked campaign instead of immediately
  becoming a residual position.
- Protection-leg taker fallback requires one-tick ask, sufficient ask depth, and
  valid net credit.
- Short-leg maker orders rest for 60 seconds in entry campaign.

## FMZ Retest Focus

After replacing the FMZ code with v3.0.20:

- Confirm a near-24h plan and observe that the status remains around the locked
  plan / entry campaign, not a refreshed candidate library.
- If the protection leg does not fill before the soft cap, confirm the bot either
  keeps maker waiting or takes ask only when the displayed Deribit book satisfies
  the one-tick and depth checks.
- After protection fills, confirm the short leg continues working on the same
  selected structure with longer maker order lifetime.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
