# Command Reference

Commands are grouped by agent task so the playbook stays workflow-oriented rather than mirroring raw help output.

## Inspect Project State

- `pizhi status`

Use this first to understand the current chapter and project state.

## Generate Candidate Work

- `pizhi continue run --count <n> --execute`

This generates candidates. It does not write source-of-truth changes by itself.

## Inspect Continue Outputs

- `pizhi checkpoints --session-id <session_id>`
- `pizhi continue resume --session-id <session_id>`

Use these commands to inspect the active continue session and resume it after applying a checkpoint.

## Apply A Chosen Result

- `pizhi checkpoint apply --id <checkpoint_id>`

This is the explicit write step. Apply mutates the source-of-truth.

## Finalize Output

- `pizhi compile --volume <n>`
- `pizhi compile --chapter <n>`
- `pizhi compile --chapters <a-b>`

Choose one explicit compile target when you are ready to build manuscript output.
