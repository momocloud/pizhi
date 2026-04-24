# 恢复指南

本指南只覆盖失败处理。所有恢复步骤都限定在当前 v1 命令面内。

## Provider 执行失败

常见表现：

- `--execute` 非零退出
- provider 拒绝凭据、base URL 或模型配置
- run 被记录但状态为 failed

恢复步骤：

1. 用 `python -m pizhi provider configure` 重新检查项目本地 provider 设置。
2. 用 `python -m pizhi runs` 查看最近运行。
3. 检查 `.pizhi/cache/runs/<run_id>/` 下的 prompt、raw payload 和 normalized output。
4. 修复凭据、路由或输入后重跑同一个生成命令。

不要对失败运行使用 `python -m pizhi apply --run-id <run_id>`。

## apply 失败

常见表现：

- `python -m pizhi apply --run-id <run_id>` 非零退出
- run target 与当前意图不一致
- normalized output 无法干净落地

恢复步骤：

1. 用 `python -m pizhi runs` 确认 run 状态和目标。
2. 检查 `.pizhi/cache/runs/<run_id>/manifest.json` 和 `normalized.md`。
3. 修复源头问题：provider 输出坏了就重跑生成命令，run id 选错了就选择正确 run。
4. 只在 run 已确认可用后重试 `python -m pizhi apply --run-id <run_id>`。

Pizhi 把真实源写入限制在 `apply` 之后，所以失败的 apply 不应故意推进项目状态。

## continue 会话中断

execute 会话中断后，优先从已有会话恢复，而不是立即新开：

```bash
python -m pizhi continue sessions
python -m pizhi checkpoints --session-id <session_id>
python -m pizhi continue resume --session-id <session_id>
```

如果已有待应用检查点：

```bash
python -m pizhi checkpoint apply --id <checkpoint_id>
python -m pizhi continue resume --session-id <session_id>
```

只有在明确想放弃旧会话并启动新批次时，才重新运行 `continue run`。

## review 或 AI review 失败

常见表现：

- `python -m pizhi review --chapter N --execute` 或 `python -m pizhi review --full --execute` 非零退出
- 报告已写入，但 AI 部分记录失败

恢复步骤：

1. 保留已生成的报告或 notes 文件；结构审校输出仍然有价值。
2. 修复 provider 配置或临时服务问题。
3. 重跑同一个 review 命令：

   ```bash
   python -m pizhi review --chapter N --execute
   python -m pizhi review --full --execute
   ```

`review --execute` 不会覆盖内置审校的权威性；重试只替换 AI 审校部分。

## 维护或扩展发现需要二次处理

`review --full` 会写入 `.pizhi/cache/review_full.md`。如果维护代理或扩展报告问题，先按报告修复真实源，再重新运行：

```bash
python -m pizhi review --full
```

不要直接编辑 `.pizhi/cache/` 下的运行产物来伪造成功状态。
