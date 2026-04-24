# Pizhi 架构

日期：2026-04-20  
状态：v1 已实现

本文件是中文归档版。默认公开架构文档仍为英文：`docs/architecture/ARCHITECTURE.md`。

## 目标

Pizhi 是面向长篇小说创作的 CLI。它把项目状态保存在磁盘上，让模型调用保持可审计，并把真实源写入限制在确定性的应用步骤中。

核心产品面包括：

- 确定性的项目初始化和文件布局
- 可插拔后端的生成流程
- 显式 `apply --run-id` 真实源更新
- 带检查点的 `continue` 执行和恢复
- 结构审校、可选 AI 审校和内置维护
- 按卷、章节或章节范围编译手稿
- 仅用于审校和维护的内部扩展 hook
- 面向外部 agent 的交付 playbook

## 边界

Pizhi 不把 LLM 输出直接当作真实源。模型或 agent 只能生成候选产物，Pizhi 负责记录、校验、归一化和应用。

`--execute` 的后端选择只影响生成和审校调用。以下命令仍然是 Pizhi 内部确定性流程：

- `pizhi apply`
- `pizhi checkpoint apply`
- `pizhi status`
- 不带 `--execute` 的 `pizhi review`
- `pizhi compile`

## 文件模型

项目初始化后，用户项目包含：

- `.pizhi/config.yaml`：项目配置和后端配置
- `.pizhi/cache/runs/`：执行记录
- `.pizhi/cache/checkpoints/`：continue 检查点
- `.pizhi/cache/continue_sessions/`：continue 会话状态
- `chapters/`：章节真实源
- `global/`：世界观、大纲、伏笔、时间线等全局真实源
- `manuscript/`：编译输出

缓存记录可以用于审计和恢复，但真实源以章节和全局文件为准。

## 执行流

典型生成流：

1. CLI 构建 prompt request。
2. provider 或 agent backend 生成候选结果。
3. Pizhi 保存 run artifact。
4. 用户或外部 agent 检查 run。
5. `pizhi apply --run-id <run_id>` 把候选结果写入真实源。

典型 continue 流：

1. `pizhi continue run --count <n> --execute` 创建会话和第一批检查点。
2. `pizhi checkpoints --session-id <session_id>` 查看待处理检查点。
3. `pizhi checkpoint apply --id <checkpoint_id>` 应用检查点。
4. `pizhi continue resume --session-id <session_id>` 继续下一批。
5. 重复直到会话完成。

## Agent 集成

仓库交付 `agents/pizhi/` 作为外部 agent 可安装的 skill/playbook。预期工作方式是：

- 用户从 `Claude Code` 等 host 入口发起任务。
- host 读取 Pizhi playbook。
- host 调用 `pizhi` CLI。
- Pizhi 在需要 `--execute` 时通过配置的 backend 调用 `opencode` 等 agent。

这让用户入口、编排器、执行后端三者分层清晰。

## 可靠性策略

Pizhi 的可靠性来自四个约束：

- 真实源写入必须显式。
- 每次执行都记录 run artifact。
- 长任务必须通过检查点恢复。
- 编译和审校基于磁盘真实源，而不是临时上下文。

这些约束会增加一步 `apply`，但能降低长篇项目中上下文丢失、模型漂移和误写真实源的风险。
