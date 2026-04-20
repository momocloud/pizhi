# Recovery Guide

This guide covers failure handling only. Every recovery step below stays within the current v1 command surface.

## Provider execution fails

Symptoms:

- `--execute` exits non-zero
- the provider rejects credentials, base URL, or model configuration
- a run is recorded but marked failed

Recovery:

1. Re-check project-local provider settings with `python -m pizhi provider configure`.
2. List recent runs with `python -m pizhi runs`.
3. Inspect the failed run under `.pizhi/cache/runs/<run_id>/` for the captured prompt, raw payload, and normalized output.
4. Re-run the same command after fixing credentials, routing, or prompt input.

Do not use `python -m pizhi apply --run-id <run_id>` for failed runs.

## Apply fails after a provider-backed run

Symptoms:

- `python -m pizhi apply --run-id <run_id>` exits non-zero
- the run target does not match the current command context
- normalized output cannot be applied cleanly

Recovery:

1. Confirm the run status and target with `python -m pizhi runs`.
2. Inspect `.pizhi/cache/runs/<run_id>/manifest.json` and `normalized.md`.
3. Fix the source issue:
   - rerun the generating command if the provider output was bad
   - choose the correct run id if you targeted the wrong artifact
4. Retry `python -m pizhi apply --run-id <run_id>` only after the run is known-good.

Pizhi keeps source-of-truth writes behind `apply`, so a failed apply should not partially advance the project intentionally.

## Continue session stops mid-run

For execute sessions, recover from the recorded session instead of starting over immediately:

```bash
python -m pizhi continue sessions
python -m pizhi checkpoints --session-id <session_id>
python -m pizhi continue resume --session-id <session_id>
```

If a checkpoint is ready to apply separately:

```bash
python -m pizhi checkpoint apply --id <checkpoint_id>
```

Use a new `continue run` only when you intentionally want a fresh session rather than resuming the stored one.

## Review or AI review fails

Symptoms:

- `python -m pizhi review --chapter N --execute` or `python -m pizhi review --full --execute` exits non-zero
- the report is written, but the AI section records a failure

Recovery:

1. Keep the generated report or notes file; structural review output is still useful even when AI review fails.
2. Fix provider configuration or transient provider issues.
3. Re-run the same review command:

   ```bash
   python -m pizhi review --chapter N --execute
   python -m pizhi review --full --execute
   ```

`review --execute` keeps built-in review output authoritative. A retry replaces the AI-review portion by running the command again.

## Maintenance or extension findings need another pass

In v1 there is no standalone maintenance command. Maintenance reruns through built-in flows:

- `python -m pizhi review --full`
- `python -m pizhi review --full --execute`
- apply-driven closure flows that invoke maintenance after deterministic updates

If an internal extension agent fails, Pizhi records the failure in the report while keeping built-in output intact. Recovery is:

1. Fix the config or provider issue behind the failing extension.
2. Re-run the owning command, usually `python -m pizhi review --full` or `python -m pizhi review --full --execute`.

Extension agents are additive only. They should never be treated as the source of truth for chapter or global files.

## When to stop and inspect files directly

Inspect the project files before retrying if any command keeps failing with the same message:

- `.pizhi/config.yaml`
- `.pizhi/cache/runs/<run_id>/`
- `.pizhi/cache/review_full.md`
- `.pizhi/chapters/chNNN/notes.md`

Repeated failures with identical inputs usually mean configuration drift, a stale run id, or a malformed provider response rather than a retryable transient error.
