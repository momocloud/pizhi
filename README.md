![Pizhi project header](docs/assets/pizhi-header.png)

# Pizhi

Pizhi is a file-backed long-form fiction workflow for planning, drafting, review, recovery, and manuscript compilation. It combines deterministic project files with backend-pluggable `--execute` flows, explicit `apply` steps, checkpointed `continue` sessions, structural review, optional AI review, and additive maintenance/report hooks.

Documentation defaults to English. 中文入口: [中文文档](docs/zh/README.md).

## Execution Stack

The recommended host entry is `Claude Code` plus the repository-shipped skill/playbook.
Pizhi is the orchestrator and source-of-truth manager in that stack.

- `Claude Code` is the external host that reads the playbook and drives commands.
- `Pizhi` is the orchestrator and source-of-truth manager.
- `opencode` is the first shipped agent execution backend for `--execute` flows.

Backend choice affects `--execute` only. Deterministic commands such as `apply`, `checkpoint apply`, `status`, `review` without `--execute`, and `compile` stay inside Pizhi's own source-of-truth pipeline.

## Install with uv

Run the CLI directly from Git without installing it permanently:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.2 pizhi --help
```

Install the CLI as a managed `uv` tool:

```bash
uv tool install git+https://github.com/momocloud/pizhi.git
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.2
```

Use the untagged Git URL when you want the latest `main`. Prefer `@v0.1.2` for stable automation and pinned installs.

## Quick Start

The examples below use `python -m pizhi`, but the installed `pizhi` entry point is equivalent.

1. Initialize a project:

   ```bash
   python -m pizhi init --project-name "Example Novel" --genre "Fantasy" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"
   ```

2. Configure the execution backend used by `--execute` flows:

   ```bash
   python -m pizhi provider configure
   ```

   Provider-backed execution still uses `pizhi provider configure`. Agent-backed execution can be configured separately:

   ```bash
   python -m pizhi agent configure --agent-backend opencode --agent-command opencode
   ```

   For unattended setup, prefer parameter mode:

   ```bash
   python -m pizhi provider configure --provider <provider> --model <model> --base-url <base_url> --api-key-env <env>
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
- `pizhi provider configure` and `pizhi agent configure` select how `--execute` steps reach a backend.
- `pizhi brainstorm`, `pizhi outline expand`, `pizhi write`, `pizhi continue run`, and `pizhi review --execute` can prepare prompts or call the configured backend.
- `pizhi runs` lists recorded executions.
- `pizhi apply --run-id <run_id>` is the explicit source-of-truth update step for successful execute runs.
- `pizhi continue run --count <n> --execute` creates checkpointed session state under `.pizhi/cache/continue_sessions/` and `.pizhi/cache/checkpoints/`; apply each generated checkpoint and resume the session before treating the chapters as complete.
- `pizhi review --full` also runs built-in maintenance and writes `.pizhi/cache/review_full.md`.
- `pizhi compile --volume`, `--chapter`, or `--chapters` builds manuscript output from drafted chapters.

## Public Docs

`agents/pizhi/` is a repository-shipped delivery artifact for external agents.

- [Getting started](docs/guides/getting-started.md)
- [Recovery guide](docs/guides/recovery.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Chinese documentation archive](docs/zh/README.md)
- [Agent playbook](agents/pizhi/AGENTS.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
