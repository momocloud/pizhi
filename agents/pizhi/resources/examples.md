# Examples

These examples show the expected external-agent workflow.

## Fresh Project Setup

```bash
pizhi init --project-name "Example Novel" --genre "Fantasy" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"
pizhi provider configure
pizhi status
```

## Continue Session With Checkpoints

```bash
pizhi status
pizhi continue run --count 3 --execute
pizhi checkpoints --session-id <session_id>
pizhi checkpoint apply --id <checkpoint_id>
pizhi continue resume --session-id <session_id>
```

Repeat the checkpoint apply and resume loop until the continue session reaches `completed`.

## Review Before Compile

```bash
pizhi status
pizhi review --full --execute
pizhi compile --volume 1
```

## Stable Git Install Example

```bash
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
```
