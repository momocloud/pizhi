# Pizhi Milestone 6 Provider First Design

## Goal

Add the first real model-execution path to Pizhi without breaking the existing prompt-only workflow.

After this milestone:

- `brainstorm`, `outline expand`, and `write` can call a real provider with `--execute`
- provider-backed execution writes auditable run artifacts into `.pizhi/cache/runs/`
- source-of-truth updates remain explicit through a second-step `apply --run-id`
- project-local provider configuration can be created through `pizhi provider configure`

## Scope

- Add a provider-backed execution path for `brainstorm`, `outline expand`, and `write`
- Add project configuration for a single OpenAI-compatible provider
- Add persistent run artifacts for prompt, raw provider output, normalized response, and run metadata
- Add `pizhi runs` and `pizhi apply --run-id ...`
- Preserve the existing prompt-only workflow when provider execution is not requested

## Non-Goals

- `continue --execute`
- Multiple provider implementations
- B-class AI semantic review
- Automatic apply after a successful run
- Project-level tuning panels for `temperature`, `timeout`, `retries`, or similar inference settings

## Primary Decisions

### 1. Provider integration is additive, not a replacement

The existing prompt-only flow remains valid. Real model execution is opt-in through `--execute`.

This keeps milestone 6 focused on provider integration instead of rewriting established deterministic flows.

### 2. Model execution and truth-source mutation stay separate

A real provider call only produces a candidate result. It does not directly mutate `.pizhi/global/`, `.pizhi/chapters/`, or other truth-source files.

The canonical write path stays explicit:

1. execute a run
2. inspect available runs
3. apply a chosen `run_id`

### 3. Milestone 6 introduces a shared execution layer

Provider execution is not implemented independently inside each command service.

Instead, commands continue to produce prompt requests and deterministic apply behavior, while a shared execution layer handles:

- provider config loading
- API key lookup
- provider invocation
- raw and normalized artifact persistence
- run manifest creation

This shared layer is the correct boundary for later milestones such as `continue --execute` and AI review.

### 4. Configuration stays in project config, secrets stay in env vars

`.pizhi/config.yaml` stores:

- `provider`
- `model`
- `base_url`
- `api_key_env`

The API key itself never enters project files. Execution resolves it from the configured environment variable at runtime.

## Design

### 1. CLI surface

Milestone 6 adds four user-facing CLI changes.

#### Provider-backed execution flags

These commands gain `--execute`:

- `pizhi brainstorm --execute`
- `pizhi outline expand --execute`
- `pizhi write --execute`

Without `--execute`, the commands keep current prompt-only behavior.

With `--execute`, the command:

1. builds the prompt request
2. persists the prompt artifact
3. invokes the configured provider
4. writes a run record into `.pizhi/cache/runs/<run_id>/`
5. prints the resulting `run_id`

#### Provider configuration command

Add:

- `pizhi provider configure`

Default mode is interactive and updates `.pizhi/config.yaml`.

It also supports non-interactive flags for scripting:

- `--provider`
- `--model`
- `--base-url`
- `--api-key-env`

Milestone 6 only needs one concrete provider value: an OpenAI-compatible adapter.

#### Run inspection command

Add:

- `pizhi runs`

This is a lightweight list view over recent run manifests. It should show at least:

- `run_id`
- `command`
- `target`
- `status`
- `created_at`

#### Apply command

Add:

- `pizhi apply --run-id <run_id>`

Milestone 6 deliberately does not support `--latest`. Applying a candidate result is a source-of-truth mutation, so the user must explicitly name the run.

### 2. Shared execution pipeline

The existing services keep their command-specific responsibilities:

- build prompt text and metadata
- know how deterministic apply works for that command

Add a shared provider-execution service that accepts a command name plus `PromptRequest` and produces a run result.

Recommended module split:

- `src/pizhi/adapters/provider_base.py`
  - provider request and response contracts
- `src/pizhi/adapters/openai_compatible.py`
  - the concrete OpenAI-compatible adapter
- `src/pizhi/services/provider_execution.py`
  - shared execution flow
- `src/pizhi/services/run_store.py`
  - run-id generation, manifest persistence, run loading, run listing
- `src/pizhi/services/apply_service.py`
  - maps `run_id` back into the existing deterministic apply path

The flow should be:

1. command service builds `PromptRequest`
2. execution service loads provider config
3. execution service resolves API key from `api_key_env`
4. adapter performs the provider call
5. execution service normalizes the provider response into an applyable text artifact
6. run store persists the run directory and manifest
7. apply service later reuses the normalized response through the existing deterministic parsers

### 3. Run artifact layout

Each run lives in:

- `.pizhi/cache/runs/<run_id>/`

Every successful or failed persisted run should be inspectable from disk.

Required files:

- `manifest.json`
- `prompt.md`
- `raw.json` when a provider response exists
- `normalized.md` when normalization succeeds
- `error.txt` when execution fails after a run directory has been created

Recommended manifest fields:

- `run_id`
- `command`
- `target`
- `status`
- `provider`
- `model`
- `base_url`
- `created_at`
- `prompt_path`
- `raw_path`
- `normalized_path`
- `referenced_files`

Milestone 6 statuses:

- `succeeded`
- `normalize_failed`
- `provider_failed`

Provider-misconfiguration cases such as missing config or missing API key should fail before creating a run directory.

### 4. Provider configuration model

Extend `ProjectConfig` with a provider section.

Recommended shape:

```yaml
provider:
  provider: openai_compatible
  model: gpt-5.4
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY
```

This milestone intentionally keeps configuration minimal.

Do not expose project-level fields such as:

- `temperature`
- `max_tokens`
- `timeout`
- `retries`

Those remain implementation defaults inside the adapter or execution service.

### 5. Apply routing

`pizhi apply --run-id ...` should not invent a new write path.

Instead, it should:

1. load the run manifest
2. verify the run status is `succeeded`
3. load `normalized.md`
4. dispatch to the existing deterministic apply path for the recorded command

Expected command routing:

- `brainstorm` run -> existing brainstorm response application
- `outline expand` run -> existing outline response application
- `write` run -> existing chapter response application

This keeps milestone 6 aligned with the architecture principle that filesystem mutation remains deterministic and explicit.

### 6. Error handling

Error boundaries should stay predictable.

#### Missing provider config

- `--execute` exits with a readable error
- no run directory is created

#### Missing configured API key env var

- `--execute` exits with a readable error naming the missing environment variable
- no run directory is created

#### Provider call failure

- create or update the run directory
- persist `prompt.md`
- write `error.txt`
- set status to `provider_failed`

#### Normalization failure

- preserve `prompt.md`
- preserve `raw.json`
- write `error.txt`
- set status to `normalize_failed`

#### Invalid apply target

`pizhi apply --run-id ...` must reject:

- unknown `run_id`
- runs not in `succeeded` state
- runs missing `normalized.md`
- runs whose recorded command is unsupported by the apply router

### 7. Backward compatibility

Milestone 6 must preserve current milestone 1-5 behavior.

Specifically:

- existing prompt-only commands keep working without provider config
- existing `--response-file` flows remain available
- maintenance behavior from milestone 5 stays on the deterministic apply side, not on provider execution

## Files

Expected new files:

- `src/pizhi/adapters/provider_base.py`
- `src/pizhi/adapters/openai_compatible.py`
- `src/pizhi/services/provider_execution.py`
- `src/pizhi/services/run_store.py`
- `src/pizhi/services/apply_service.py`
- `src/pizhi/commands/provider_cmd.py`
- `src/pizhi/commands/runs_cmd.py`
- `src/pizhi/commands/apply_cmd.py`
- `tests/unit/test_run_store.py`
- `tests/unit/test_provider_execution.py`
- `tests/unit/test_openai_compatible.py`
- `tests/integration/test_provider_configure_command.py`
- `tests/integration/test_runs_command.py`
- `tests/integration/test_apply_command.py`

Expected modified files:

- `src/pizhi/core/config.py`
- `src/pizhi/cli.py`
- `src/pizhi/commands/brainstorm_cmd.py`
- `src/pizhi/commands/outline_cmd.py`
- `src/pizhi/commands/write_cmd.py`
- `src/pizhi/services/brainstorm_service.py`
- `src/pizhi/services/outline_service.py`
- `src/pizhi/services/write_service.py`
- `tests/unit/test_config.py`

## Testing Strategy

### Unit tests

- config round-trip with provider settings
- provider configure parsing and update behavior
- OpenAI-compatible request construction
- run-store manifest persistence and listing
- execution service success path
- execution service provider-failure path
- execution service normalization-failure path
- apply routing for supported commands
- apply rejection for missing or invalid run states

### Integration tests

- `pizhi provider configure` interactive-safe or parameter-mode update of `.pizhi/config.yaml`
- `brainstorm --execute`, `outline expand --execute`, and `write --execute` success paths with a stubbed adapter
- `pizhi runs` lists recent runs in a readable summary
- `pizhi apply --run-id ...` routes a successful run back through deterministic application
- prompt-only behavior remains unchanged when `--execute` is omitted

### Regression rule

Milestones 1-5 remain green. Provider-backed execution must be additive, not destabilizing.

## Acceptance Criteria

- provider settings can be created or updated through `pizhi provider configure`
- `brainstorm`, `outline expand`, and `write` can execute against an OpenAI-compatible endpoint with `--execute`
- each provider-backed run writes auditable artifacts into `.pizhi/cache/runs/<run_id>/`
- `pizhi runs` can list available runs with enough metadata to choose one safely
- `pizhi apply --run-id ...` can apply successful runs through the existing deterministic write path
- missing config, missing API key env vars, provider failures, and normalization failures produce clear and bounded behavior
- the existing prompt-only workflow still works unchanged
