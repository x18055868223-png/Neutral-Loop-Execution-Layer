# Neutral Loop Execution Layer

Human Audit Gate execution-layer handoff package for GPT-5.5 Pro continuation.

This repository contains the current independent execution-layer deliverable only. It does not include the signal-layer FMZ artifact and must not be treated as proof of FMZ dry-run, exchange read-only validation, or live readiness.

## Current Artifact

- FMZ artifact: `artifacts/spm_manual_gate_execution_fmz.py`
- Editable source: `realsrc/src/`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- Version: `STRATEGY_VERSION = "3.0.0-manual-gate"`
- Status: `MANUAL_GATE_PLAN_READY`
- SHA256 for artifact/source bundle: `3F05A45695AEB46AF16B895E6A5302C415C6D164A222874C427EEE2EFD18BD6C`

## Boundary

The execution layer is independent from the signal layer. Current planning input comes from FMZ/manual parameters, not from signal files, G keys, receiver modules, or external lineage packages.

Main path:

`manual audit gate params -> Deribit option-chain -> same-expiry vertical candidates -> S:PM / execution feasibility / VRP / budget filters -> confirm code -> precommit -> entry campaign`

Existing positions continue through position management, exit, hedge, and recovery even when manual planning is disabled.

## Safety Defaults

The current artifact keeps live trading gates off:

- `ALLOW_ENTRY_TRADING = False`
- `ALLOW_EXIT_TRADING = False`
- `ALLOW_HEDGE_TRADING = False`
- `DRY_RUN_PASSED = False`

Do not flip these defaults in routine development. `DRY_RUN_PASSED` requires real FMZ robot interaction dry-run plus exchange read-only verification, neither of which is claimed by this handoff.

## Development Workflow

Edit source first:

```powershell
cd realsrc
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe build_bundle.py --check
```

After `build_bundle.py --check`, copy the generated bundle to `artifacts/spm_manual_gate_execution_fmz.py` and refresh `CHECKSUMS.txt`.

See `CHATGPT5.5_PRO.md` for the full continuation brief.
