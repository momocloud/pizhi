# Getting Started

This runbook covers the supported v1 flow from initialization through compilation. Command examples use `python -m pizhi`, but the installed `pizhi` entry point is equivalent.
Use `README.md` as the public landing page for the project and governance links.

## Install the CLI with uv

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1
```

Use the untagged Git URL when you want the latest `main`. Prefer `@v0.1.1` for stable automation and pinned installs.

## 1. Initialize a project

```bash
python -m pizhi init --project-name "Example Novel" --genre "Fantasy" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"
```

This creates the hidden `.pizhi/` working tree, the visible `manuscript/` output directory, and the baseline global/chapter files.

## 2. Configure provider access

If you plan to use `--execute`, configure the project-local provider settings first:

```bash
python -m pizhi provider configure
```

The interactive flow stores the base route plus optional model overrides such as `--brainstorm-model`, `--continue-model`, and `--review-model`.

## 3. Use provider-backed generation with explicit apply

Provider-backed commands record auditable run artifacts before any source-of-truth mutation. The canonical pattern is:

```bash
python -m pizhi brainstorm --execute
python -m pizhi runs
python -m pizhi apply --run-id <run_id>
```

The same pattern applies to other provider-backed generation commands:

```bash
python -m pizhi outline expand --chapters 1-3 --execute
python -m pizhi write --chapter 1 --execute
python -m pizhi apply --run-id <run_id>
```

Use `pizhi apply --run-id` only with successful runs that match the command and target you intend to update.

## 4. Continue with checkpointed sessions

For multi-chapter generation, use the canonical execute form:

```bash
python -m pizhi continue run --count 3 --execute
```

Canonical command shape: `pizhi continue run --count <n> --execute`

Prompt-only mode is still available when you already have response files:

```bash
python -m pizhi continue run --count 3 --outline-response-file outline.md --chapter-responses-dir responses
```

To inspect or resume a paused execute session:

```bash
python -m pizhi continue sessions
python -m pizhi checkpoints --session-id <session_id>
python -m pizhi continue resume --session-id <session_id>
python -m pizhi checkpoint apply --id <checkpoint_id>
```

`continue resume` restarts the stored session. `checkpoint apply` applies the stored checkpoint payload explicitly.

## 5. Review and maintenance

Structural review works without provider execution:

```bash
python -m pizhi review --chapter 3
python -m pizhi review --full
```

Provider-backed review uses the same execute flag:

```bash
python -m pizhi review --chapter 3 --execute
python -m pizhi review --full --execute
```

Canonical command shapes:

- `pizhi review --chapter <n> --execute`
- `pizhi review --full --execute`

`pizhi review --execute` runs structural review first, then optional AI review, and writes partitioned notes or a full review report. `pizhi review --full` also runs built-in maintenance. In v1, maintenance does not have a standalone CLI; it runs inside full review and apply-driven closure flows.

If the project config defines internal extension agents, their `review` findings are appended during `review --execute`. `maintenance` findings appear in `review --full --execute`, `apply --run-id`, and checkpoint-apply closure flows. Non-`--execute` `review --full` stays deterministic and only reruns built-in maintenance.

## 6. Compile manuscript output

Compile visible manuscript output after chapters have been drafted:

```bash
python -m pizhi compile --volume 1
python -m pizhi compile --chapter 12
python -m pizhi compile --chapters 10-15
```

Compilation reads drafted chapter material and writes the requested manuscript slice into `manuscript/`.

## 7. Common file locations

- `.pizhi/config.yaml`: project and provider configuration
- `.pizhi/cache/runs/<run_id>/`: provider execution artifacts such as prompts and normalized output
- `.pizhi/cache/review_full.md`: full-project review report
- `.pizhi/chapters/chNNN/notes.md`: chapter review notes
- `manuscript/`: compiled volume or chapter outputs

## 8. Recommended day-to-day loop

1. `python -m pizhi status`
2. `python -m pizhi continue run --count <n> --execute` or `python -m pizhi write --chapter <n> --execute`
3. `python -m pizhi runs`
4. `python -m pizhi apply --run-id <run_id>`
5. `python -m pizhi review --chapter <n>` or `python -m pizhi review --full --execute`
6. `python -m pizhi compile --volume <n>`

Use the [recovery guide](recovery.md) when a provider call, apply step, continue session, or review run does not complete cleanly.
