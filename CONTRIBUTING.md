# Contributing

Thanks for helping improve Pizhi.

## Setup

```bash
python -m pip install -e .
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
