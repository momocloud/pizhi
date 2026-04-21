# Failure Recovery

Use this guide when the playbook flow cannot continue cleanly.

## Provider Not Configured

If a provider-backed command fails because the provider is not configured, stop and configure the CLI before retrying.

This is the `provider not configured` recovery branch:

```bash
pizhi provider configure --provider <provider> --model <model> --base-url <base_url> --api-key-env <env>
```

Use bare `pizhi provider configure` only when a human is present to answer interactive prompts. Do not keep retrying `--execute` commands until provider configuration is in place.

## Failed Run

If a run fails, inspect the recorded run state before deciding what to do next:

```bash
pizhi runs
```

Do not apply a failed run. Only apply successful outputs.

## Rejected Apply

If a run-based candidate should not become source-of-truth, do not force it through:

- leave the run unapplied
- generate a new candidate run
- only use `pizhi apply --run-id <run_id>` for a successful run you intend to keep

If you are in a checkpointed continue flow, keep the checkpoint model separate:

- review checkpoints first
- only use `pizhi checkpoint apply --id <checkpoint_id>` when you have chosen the checkpoint you want to keep

## Interrupted Checkpoint Flow

If the continue flow is interrupted, return to the active session explicitly:

```bash
pizhi continue sessions
pizhi checkpoints --session-id <session_id>
pizhi continue resume --session-id <session_id>
```

Use checkpoint apply --id <checkpoint_id> only after reviewing the available checkpoint outputs.

## Stable Git Install Path

For pinned automation, prefer a released tag such as `v0.1.0` once it exists. Before that tag exists, use the untagged repository install path instead of a non-existent pinned ref.
