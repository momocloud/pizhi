# 开始使用

本指南覆盖从初始化到编译的 v1 支持流程。命令示例使用 `python -m pizhi`，安装后的 `pizhi` 命令等价。

## 1. 安装 CLI

```bash
uvx --from git+https://github.com/momocloud/pizhi.git pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git
uvx --from git+https://github.com/momocloud/pizhi.git@v0.1.1 pizhi --help
uv tool install git+https://github.com/momocloud/pizhi.git@v0.1.1
```

未带 tag 的 Git URL 适合跟随最新 `main`。稳定自动化建议使用 `@v0.1.1`。

## 2. 初始化项目

```bash
python -m pizhi init --project-name "Example Novel" --genre "Fantasy" --total-chapters 60 --per-volume 15 --pov "Third Person Limited"
```

该命令会创建隐藏的 `.pizhi/` 工作树、可见的 `manuscript/` 输出目录，以及基础全局文件和章节文件。

## 3. 配置执行后端

如果计划使用 `--execute`，先配置项目本地后端：

```bash
python -m pizhi provider configure
```

如果希望 `--execute` 通过 agent 后端运行，而不是直接调用 provider 路由，可以配置：

```bash
python -m pizhi agent configure --agent-backend opencode --agent-command opencode
```

推荐栈：

- `Claude Code + skill` 作为外部入口
- `Pizhi` 作为编排器和真实源管理器
- `opencode` 作为首个 agent 执行后端

## 4. 生成并显式落真源

带 `--execute` 的命令会先记录可审计的运行产物，不会直接改真实源。典型流程：

```bash
python -m pizhi brainstorm --execute
python -m pizhi runs
python -m pizhi apply --run-id <run_id>
```

其他生成命令也使用同样模式：

```bash
python -m pizhi outline expand --chapters 1-3 --execute
python -m pizhi write --chapter 1 --execute
python -m pizhi apply --run-id <run_id>
```

只对成功运行使用 `pizhi apply --run-id`，并确认 run 的命令和目标与当前意图一致。

## 5. 使用检查点续写

多章节生成使用检查点会话：

```bash
python -m pizhi continue run --count 3 --execute
```

规范命令形态是：`pizhi continue run --count <n> --execute`。

查看会话和检查点：

```bash
python -m pizhi continue sessions
python -m pizhi checkpoints --session-id <session_id>
```

应用检查点后继续：

```bash
python -m pizhi checkpoint apply --id <checkpoint_id>
python -m pizhi continue resume --session-id <session_id>
```

重复应用检查点和恢复会话，直到会话状态为 `completed`。

## 6. 审校与编译

章节审校：

```bash
python -m pizhi review --chapter <n>
python -m pizhi review --chapter <n> --execute
```

全局审校和维护：

```bash
python -m pizhi review --full
python -m pizhi review --full --execute
```

编译手稿：

```bash
python -m pizhi compile --volume 1
python -m pizhi compile --chapter 1
python -m pizhi compile --chapters 1-10
```

编译只读取已经完成的章节真实源，不会调用外部模型。
