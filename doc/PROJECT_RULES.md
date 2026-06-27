# Project Rules

## Version Cleanup

- Each small-version delivery must remove obsolete compatibility paths after a strict reference audit.
- Before deleting old code, run `rg` for every old entrypoint/function name and confirm current call sites.
- After deleting old code, run `rg` again and keep only intentional data-field history, not callable legacy gates.
- Do not leave unused fallback implementations "just in case"; if the workflow no longer uses it, delete it.
- Add the smallest runnable test or compile check that would fail if the old path comes back.

## Delivery Boundary

- `artifacts/最新交付` contains the current operator-facing file.
- `artifacts/` keeps versioned backups.
- Do not claim FMZ dry-run, exchange read-only validation, or live readiness from local tests.

## FMZ Runtime Notes

- FMZ Python robots may not define global `HttpQuery`; external HTTP calls should use Python `urllib` in the delivered strategy file.
- Confirmation-code interaction must be configured as command `执行` with type `string`; never use `number` because codes contain letters.
