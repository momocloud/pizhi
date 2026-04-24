# Pizhi 中文文档归档

Pizhi 是一个 LLM 辅助长篇小说创作工作流，用文件系统保存项目状态，并通过显式 `apply`、检查点续写、结构审校、可选 AI 审校和手稿编译来支撑长篇创作。

本目录是中文文档归档。仓库默认公开入口仍然是英文文档：

- 根目录 `README.md`
- `docs/guides/getting-started.md`
- `docs/guides/recovery.md`
- `docs/architecture/ARCHITECTURE.md`

## 执行栈

推荐入口是 `Claude Code` 加仓库交付的 agent skill/playbook。Pizhi 自身负责调度命令、维护真实源文件、记录运行产物，并把真实源更新限制在确定性的 `apply` 步骤中。

- `Claude Code`：外部统一入口，读取 playbook 并驱动 CLI。
- `Pizhi`：编排器和真实源管理器。
- `opencode`：首个随仓库交付的 agent 执行后端，用于 `--execute` 流程。

后端选择只影响 `--execute`。`apply`、`checkpoint apply`、`status`、不带 `--execute` 的 `review`、`compile` 等确定性命令仍在 Pizhi 内部完成。

## 安装

直接从 Git 运行 CLI：

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help
```

作为 `uv` 管理的工具安装：

```bash
uv tool install git+https://github.com/momocloud/pizhi.git
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1
```

未带 tag 的 Git URL 适合跟随最新 `main`。自动化脚本和稳定安装建议固定到 `@v0.1.1`。

## 中文文档

- [开始使用](guides/getting-started.md)
- [恢复指南](guides/recovery.md)
- [架构](architecture/ARCHITECTURE.md)

## 核心工作流

1. `pizhi init` 创建项目树和 `.pizhi/config.yaml`。
2. `pizhi provider configure` 或 `pizhi agent configure` 配置 `--execute` 后端。
3. `pizhi brainstorm`、`pizhi outline expand`、`pizhi write`、`pizhi continue run`、`pizhi review --execute` 负责准备提示或调用后端。
4. `pizhi runs` 查看运行记录。
5. `pizhi apply --run-id <run_id>` 显式把成功运行写入真实源。
6. `pizhi continue run --count <n> --execute` 创建检查点会话；每个检查点需要先 `checkpoint apply`，再 `continue resume`。
7. `pizhi review --full` 运行全局审校和维护。
8. `pizhi compile --volume`、`--chapter` 或 `--chapters` 编译手稿输出。
