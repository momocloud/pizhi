# Stage 1 Smoke Report

- Date: `2026-04-22`
- Harness entrypoint: `python scripts/verification/e2e_claude_opencode.py --stage stage1`
- Final inspected temp project: `C:/Users/kywin/ownProject/noval/tmp/pizhi-e2e-claude-opencode-2026-04-22T13-57-53`

## Outcome Summary

The Stage 1 harness rerun completed with exit code 0 and returned cleanly before the outer shell timeout.

This rerun validates the harness boundary fix:

- Claude is launched with `--add-dir` scoped to `agents/pizhi`
- the stage prompt now tells Claude that the repo/playbook are read-only
- the prompt tells Claude to stop after stage-end review and compile

The rerun itself did not regenerate Stage 1 manuscript artifacts in the temp project. Claude responded that it did not see the validation task content, so this archive records the clean host exit rather than a full artifact-producing run.

## Commands Run

- `python scripts/verification/e2e_claude_opencode.py --stage stage1`
- `python -m pytest tests/unit/test_e2e_claude_opencode.py -q`

## Artifact Index

The clean rerun did not produce new Stage 1 artifacts for this archive.

## Manual Inspection Notes

- The harness returned exit code 0.
- The host command completed without the earlier outer-timeout failure mode.
- No product code under `src/pizhi/**` was modified for this fix.
