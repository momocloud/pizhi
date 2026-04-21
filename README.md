# Pizhi

Pizhi is a file-backed long-form fiction workflow for planning, drafting, review, recovery, and manuscript compilation. It combines deterministic project files with provider-backed execution, explicit `apply` steps, checkpointed `continue` sessions, structural review, optional AI review, and additive maintenance/report hooks.

## Install with uv

Run the CLI directly from Git without installing it permanently:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
```

Install the CLI as a managed `uv` tool:

```bash
uv tool install git+https://github.com/momocloud/pizhi.git
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0
```

Before the `v0.1.0` release tag is created on merged `main`, the untagged Git URL is the immediately valid install path. Once that tag exists, the `@v0.1.0` forms become the stable path for automation and pinned installs.

## Quick Start

The examples below use `python -m pizhi`, but the installed `pizhi` entry point is equivalent.

1. Initialize a project:

   ```bash
   python -m pizhi init --project-name "Example Novel" --genre "Fantasy" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"
   ```

2. Configure the provider route used by `--execute` flows:

   ```bash
   python -m pizhi provider configure
   ```

3. Generate content with an execute-first flow, then apply the selected run:

   ```bash
   python -m pizhi brainstorm --execute
   python -m pizhi runs
   python -m pizhi apply --run-id <run_id>
   ```

4. Continue through checkpointed execution before review and compilation:

   ```bash
   python -m pizhi continue run --count 3 --execute
   python -m pizhi checkpoints --session-id <session_id>
   python -m pizhi checkpoint apply --id <checkpoint_id>
   python -m pizhi continue resume --session-id <session_id>
   ```

   Repeat checkpoint apply and resume until the continue session reaches `completed`, then run:

   ```bash
   python -m pizhi review --full --execute
   python -m pizhi compile --volume 1
   ```

## Canonical Workflow

- `pizhi init` creates the project tree and `.pizhi/config.yaml`.
- `pizhi provider configure` stores the provider and model routes used by provider-backed commands.
- `pizhi brainstorm`, `pizhi outline expand`, `pizhi write`, `pizhi continue run`, and `pizhi review --execute` can prepare prompts or call the configured provider.
- `pizhi runs` lists recorded provider executions.
- `pizhi apply --run-id <run_id>` is the explicit source-of-truth update step for provider-backed runs.
- `pizhi continue run --count <n> --execute` creates checkpointed session state under `.pizhi/cache/continue_sessions/` and `.pizhi/cache/checkpoints/`; apply each generated checkpoint and resume the session before treating the chapters as complete.
- `pizhi review --full` also runs built-in maintenance and writes `review_full.md`.
- `pizhi compile --volume`, `--chapter`, or `--chapters` builds manuscript output from drafted chapters.

## Public Docs

- [Getting started](docs/guides/getting-started.md)
- [Recovery guide](docs/guides/recovery.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Agent playbook](agents/pizhi/AGENTS.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
