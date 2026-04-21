# Pizhi Agent Playbook

Use this directory as the entrypoint for an external agent that will drive the `pizhi` CLI.

1. Install the `pizhi` CLI first.
2. Load `agents/pizhi/`.
3. Start at this file: `AGENTS.md`.
4. Read the supporting resources in `resources/` before generating or applying changes.

## Workflow Rules

- Start by inspecting the current project state with `pizhi status`.
- Use `pizhi continue run --count <n> --execute` to generate candidate work.
- Review the generated checkpoints with `pizhi checkpoints --session-id <session_id>`.
- Apply the selected checkpoint with `pizhi checkpoint apply --id <checkpoint_id>`.
- `--execute` generates candidates. Explicit apply mutates the source-of-truth.
- Do not edit `.pizhi/` directly.

## Read Next

- `resources/workflow.md`
- `resources/commands.md`
- `resources/failure-recovery.md`
- `resources/examples.md`
