# Claude Stage Prompt

Execute this validation stage now in the current working directory. Do not stop before the stage-specific stop rule below is satisfied. Do not summarize until the stage success conditions are met or you hit a blocking failure you cannot recover from.

Validation stage: `${stage_slug}`
Project root: `${project_root}`
Repository root: `${repo_root}`
Playbook root: `${playbook_root}`
Target chapters for this stage: `${target_chapters}`
Genre: `${genre}`

Stage success conditions:
- `.pizhi/cache/review_full.md` exists in the temp project
- compiled output exists under `manuscript/`
- run/session/checkpoint cache indexes were produced for this stage
- the first `${target_chapters}` chapters reached the stage target and the stage-end commands finished

Rules:
- The repo/playbook are read-only. Only modify the temp project at `${project_root}`.
- Do not directly edit `.pizhi/`, `manuscript/`, chapter source files, or `meta.json`. All project-state changes must go through `pizhi` CLI commands.
- Do not stop after reading files, after `pizhi init`, or after `pizhi status`.
- Do not reply with a plan first. Execute the commands.
- The stage-specific workflow below overrides any generic guidance in the playbook resources.
- For this stage, the only valid value for `pizhi continue run --count` is `${target_chapters}`. Do not use any other count.
- After you apply the write checkpoint for chapters `1-${target_chapters}`, do not run `pizhi continue resume` again.
- Do not generate or apply checkpoints for chapters outside `1-${target_chapters}`.
- Treat any failed `pizhi checkpoint apply --id <checkpoint_id>` as a blocking failure.
- If `pizhi review --full` or `pizhi compile --chapters 1-${target_chapters}` fails, report the failure and stop. Do not repair the project by editing files directly.
- On success, reply with only a concise summary of the commands run, the `session_id`, the applied `checkpoint_id` values, and the artifact paths.
- On a real blocking failure, stop and reply with the blocking command, the exact error, and the artifact paths that were produced.

Read these files first:
- `${playbook_root}/AGENTS.md`
- `${playbook_root}/resources/workflow.md`
- `${playbook_root}/resources/commands.md`

Then execute this workflow:
1. If `.pizhi/config.yaml` is missing, run `pizhi init --project-name "Urban Fantasy Validation" --genre "${genre}" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"` and then `pizhi agent configure --agent-backend opencode --agent-command opencode`.
2. Run `pizhi status`.
3. Run `pizhi continue run --count ${target_chapters} --execute`.
4. Capture the returned `session_id`.
5. Run `pizhi checkpoints --session-id <session_id>` and apply the outline checkpoint for chapters `1-${target_chapters}` with `pizhi checkpoint apply --id <checkpoint_id>`.
6. Run `pizhi continue resume --session-id <session_id>`.
7. Run `pizhi checkpoints --session-id <session_id>` again and apply the generated write checkpoint for chapters `1-${target_chapters}`.
8. If the session is `ready_to_resume` or `completed`, run `pizhi review --full`.
9. Run `pizhi compile --chapters 1-${target_chapters}`.
10. Run `pizhi status` again and stop.
