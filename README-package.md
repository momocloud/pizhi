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

Before the `v0.1.0` release tag is created on merged `main`, the untagged Git URL is the immediately valid install path. Once that tag exists, the `@v0.1.0` forms become the stable path for automation and pinned installs.
