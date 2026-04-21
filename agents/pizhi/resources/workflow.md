# Author Workflow

This workflow covers the agent-facing author loop from installation through compilation.

## 1. Install The CLI

Install the `pizhi` CLI with the package manager available in your environment.

After the CLI is installed, load `agents/pizhi/` and open `AGENTS.md` first.

## 2. Inspect The Current Project State

Before generating anything, inspect the current repository state:

```bash
pizhi status
```

Use this to understand chapter progress and whether the project already has draft, review, or compile work in flight.

## 3. Generate Provider-Backed Candidates

For provider-backed commands such as `brainstorm`, `outline expand`, or `write`, generate a candidate first:

```bash
pizhi write --chapter <n> --execute
pizhi runs
pizhi apply --run-id <run_id>
```

`--execute` generates candidates. It does not mutate the source-of-truth by itself. Use `pizhi runs` to inspect the available provider outputs, then apply the selected successful run explicitly.

## 4. Generate Checkpointed Continue Work

For the checkpointed continue flow, generate candidates like this:

```bash
pizhi continue run --count <n> --execute
```

This creates a continue session with checkpoints instead of a single run to apply.

## 5. Review The Generated Checkpoints

List the generated checkpoints for the active continue session:

```bash
pizhi checkpoints --session-id <session_id>
```

Use this output to inspect the available checkpoint identifiers and choose the candidate you want to keep.

## 6. Apply The Chosen Checkpoint

Apply the selected checkpoint explicitly:

```bash
pizhi checkpoint apply --id <checkpoint_id>
```

This is the mutating step. Explicit checkpoint application updates the source-of-truth.

## 7. Resume The Session

After applying a checkpoint, continue the session:

```bash
pizhi continue resume --session-id <session_id>
```

Repeat the generate, review, apply, and resume loop until the continue session reaches `completed`.

## 8. Review Before Compilation

Before compiling the manuscript, run the appropriate review flow and confirm the project state again:

```bash
pizhi review --full --execute
```

If you are reviewing a narrower target, use the appropriate chapter-scoped review command instead.

```bash
pizhi status
```

## 9. Compile The Final Output

Compile with an explicit target:

```bash
pizhi compile --volume <n>
```

You can also compile a single chapter or a chapter range with `--chapter <n>` or `--chapters <a-b>`.
