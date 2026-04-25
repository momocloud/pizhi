# Contributing

Thanks for helping improve Pizhi.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Test

Run the full local check before opening a pull request:

```bash
python -m pytest tests/unit tests/integration -q --tb=short -rfE
```

## Pull Requests

- Keep changes focused and easy to review.
- Include tests when behavior changes.
- Update docs when user-facing behavior or workflow changes.
- Prefer clear commit messages and concise PR descriptions.

## Documentation

- Public docs belong in `README.md`, `docs/`, and repository governance files.
- Internal specs belong in `meta/specs`.
- Internal plans belong in `meta/plans`.

## Git Distribution Baseline

- The current public stability tag for Git-backed installs is `v0.1.2`.
- Stable consumer examples should prefer `@v0.1.2`.
- Any repository change that alters install or packaging behavior must update the public docs and the distribution contract tests.
