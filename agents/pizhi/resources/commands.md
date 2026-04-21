# Command Reference

Commands are grouped by agent task so the playbook stays workflow-oriented rather than mirroring raw help output.

## Bootstrap

- `pizhi init`
- `pizhi provider configure --provider <provider> --model <model> --base-url <base_url> --api-key-env <env>`

## Inspect Project State

- `pizhi status`

Use this first to understand the current chapter and project state.

## Generate Candidate Work

- `pizhi brainstorm --execute`
- `pizhi outline expand --chapters <a-b> --execute`
- `pizhi write --chapter <n> --execute`
- `pizhi continue run --count <n> --execute`

These commands generate candidates. They do not write source-of-truth changes by themselves.

## Inspect And Apply Provider Runs

- `pizhi runs`
- `pizhi apply --run-id <run_id>`

Use these commands for provider-backed packet flows such as `brainstorm`, `outline expand`, and `write`.

## Inspect Continue Outputs

- `pizhi continue sessions`
- `pizhi checkpoints --session-id <session_id>`

Use these commands to inspect available continue sessions and checkpoint outputs.

## Apply A Chosen Result

- `pizhi checkpoint apply --id <checkpoint_id>`

This is the explicit write step. Apply mutates the source-of-truth.

## Advance The Session

- `pizhi continue resume --session-id <session_id>`

Use this after applying a checkpoint to continue the session toward completion.
Do not use `pizhi apply --run-id <run_id>` for continue checkpoints.

## Review Before Compilation

- `pizhi review --full --execute`
- `pizhi review --chapter <n> --execute`

Use the appropriate review command before compiling manuscript output.

## Finalize Output

- `pizhi compile --volume <n>`
- `pizhi compile --chapter <n>`
- `pizhi compile --chapters <a-b>`

Choose one explicit compile target when you are ready to build manuscript output.
