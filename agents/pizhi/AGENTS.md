# Pizhi Agent Playbook

Use this directory as the entrypoint for an external agent that will drive the `pizhi` CLI.

Recommended stack:

- `Claude Code + skill` is the host entry.
- `Pizhi` owns orchestration and source-of-truth updates.
- `opencode` can serve as the first shipped agent backend for `--execute`.

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
- Backend selection changes how `--execute` gets candidates. It does not change deterministic commands such as `apply`, `checkpoint apply`, or `compile`.
- Do not edit `.pizhi/` directly.
- Do not change provider configuration unless the user asked.

## Read Next

- [workflow.md](resources/workflow.md)
- [commands.md](resources/commands.md)
- [failure-recovery.md](resources/failure-recovery.md)
- [examples.md](resources/examples.md)
