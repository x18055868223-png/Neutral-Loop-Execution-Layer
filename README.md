# Neutral Loop Execution Layer

Human Audit Gate execution-layer handoff package for GPT-5.5 Pro continuation.

This repository contains the current independent execution-layer deliverable only. It does not include the signal-layer FMZ artifact and must not be treated as proof of FMZ dry-run, exchange read-only validation, or live readiness.

## Current Artifact

- FMZ artifact: `artifacts/spm_manual_gate_execution_fmz.py`
- Latest FMZ delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_13.py`
- Editable source: `realsrc/src/`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- Version: `STRATEGY_VERSION = "3.0.13-manual-gate"`
- Status: live-test defaults with manual confirm-code gate

## Boundary

The execution layer is independent from the signal layer. Current planning input comes from FMZ/manual live config, not from signal files, receiver modules, or external lineage packages.

Main path:

`manual live config -> Deribit option-chain -> nearest-24h vertical candidates -> S:PM / execution feasibility / VRP validity / budget filters -> confirm code -> precommit -> entry campaign`

Existing positions continue through position management, exit, hedge, and recovery even when manual planning is disabled.

## Live-Test Defaults

The current artifact defaults to the user's small live-test posture:

- `RUN_PROFILE = "LIVE"`
- `DRY_RUN_PASSED = True`
- `ALLOW_ENTRY_TRADING = True`
- `ALLOW_EXIT_TRADING = True`
- `ALLOW_HEDGE_TRADING = True`
- `RISK_EXIT_MAX_SPEND = 0.001`

Do not claim FMZ live readiness from local checks alone. Local tests prove only the code and artifact boundary; live acceptance comes from the user's FMZ logs and exchange state.

## Development Workflow

Edit source first:

```powershell
cd realsrc
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe build_bundle.py --check
```

After `build_bundle.py --check`, copy the generated bundle to a versioned backup under `artifacts/`, update `artifacts/spm_manual_gate_execution_fmz.py`, and keep `artifacts/最新交付/` to exactly one current versioned file.

See `CHATGPT5.5_PRO.md` for the full continuation brief.
