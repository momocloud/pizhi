# Pizhi

Pizhi is a file-backed long-form fiction workflow for planning, drafting, review, recovery, and manuscript compilation.

## Install with uv

Run the packaged CLI straight from Git:

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.0 pizhi --help
```

Install it as a managed `uv` tool:

```bash
uv tool install git+https://github.com/momocloud/pizhi.git
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.0
```

Prefer `@v0.1.0` for automation and stable environments. Use the untagged repository only when you intentionally want to follow the latest `main` branch tip.
