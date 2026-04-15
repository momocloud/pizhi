# 辟芷（Pizhi）— 融合架构设计文档

> 版本：1.2.0-merged | 日期：2026-04-15
> 来源：合并 GLM 设计 + Kimi 设计 + 双向评审意见 + OpenAI 评审

---

## 一、项目定位

辟芷是一个面向 Claude Code 的 skill，让 AI 与人类作者以 **自回归 + 渐进式披露** 的方式协同完成长篇小说创作。

核心理念：

- **文件即记忆**：文件系统是持久化存储，上下文是易失工作内存。
- **章节自治**：每章拥有独立的元数据快照，不依赖对全文的实时回溯。
- **渐进披露**：写作时只加载必要的上下文窗口，而非全量扫描。
- **可验证的一致性**：内置结构化矛盾检测，分脚本校验与 AI 审查两层。
- **Patch 而非追加**：世界观等全局设定通过显式 diff 更新，防止无限膨胀。

---

## 二、目录结构

```
<project_root>/
├── .pizhi/                              # 辟芷工作目录（隐藏，AI 自动管理）
│   ├── config.yaml                      # 项目配置
│   │
│   ├── global/                          # 全局元数据（当前有效状态）
│   │   ├── synopsis.md                  # 故事总体简介
│   │   ├── synopsis_candidate.md        # synopsis 更新候选（仅在替换校验期间存在）
│   │   ├── worldview.md                 # 当前有效世界观（非追加，按 patch 更新）
│   │   ├── timeline.md                  # 全局时间线（近 50 章，更早的归档到 archive/）
│   │   ├── foreshadowing.md             # 伏笔追踪器（active / referenced / resolved / abandoned）
│   │   ├── characters_index.md          # 全局角色注册表（身份、别名、长期属性）
│   │   ├── outline_global.md            # 全书分卷大纲（人类可读蓝图）
│   │   └── rules.md                     # 写作规则与风格约束
│   │
│   ├── chapters/                        # 章节数据（自回归核心，每章自包含）
│   │   ├── index.jsonl                  # 章节索引/状态机（机器可读真源）
│   │   ├── ch000/                       # 故事开始前的初始快照（灵感模式产出）
│   │   │   ├── characters.md            # 初始角色设定
│   │   │   └── relationships.md         # 初始人物关系
│   │   │
│   │   ├── ch001/
│   │   │   ├── outline.md               # 本章大纲
│   │   │   ├── text.md                  # 本章正文
│   │   │   ├── characters.md            # 本章活跃角色状态截面
│   │   │   ├── relationships.md         # 本章结束时的人物关系快照
│   │   │   ├── worldview_patch.md       # 本章的世界观变更（仅在变更时存在）
│   │   │   └── notes.md                 # 作者批注 + AI 一致性检查结果
│   │   │
│   │   ├── ch002/
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── hooks/                           # 创作流程钩子
│   │   ├── pre_chapter.md               # 每章开写前的检查清单
│   │   ├── post_chapter.md              # 每章写完后的自检清单
│   │   └── consistency_check.md         # 一致性审查模板
│   │
│   ├── cache/                           # 跨会话状态
│   │   ├── last_session.md              # 上次会话摘要（停在第几章、待办事项）
│   │   └── pending_actions.md           # 未完成的待办
│   │
│   └── archive/                         # 归档目录（每 50 章自动归档）
│       ├── timeline_ch001-050.md        # 已归档的时间线条目
│       └── foreshadowing_ch001-050.md   # 已归档的已回收/已放弃伏笔
│
├── manuscript/                          # 用户可见的成品正文
│   ├── vol_01.md                        # 分卷合辑（从 chapters/ 编译）
│   ├── vol_02.md
│   └── ...
│
└── references/                          # 参考资料（用户自行管理）
    └── ...
```

### 设计决策说明

| 决策 | 理由 |
|------|------|
| `.pizhi/` 隐藏目录 + `manuscript/` 分离 | 工作数据与用户成品物理隔离，降低认知负担 |
| 每章一个目录 | 自包含：一个目录看完一章的全部信息，人类审阅友好 |
| 快照拆为 `characters.md` + `relationships.md` | 按类型独立，可单独加载，避免「只想看关系变化却加载全部」的浪费 |
| 世界观用 patch 而非追加 | 防止 260 章后 `worldview.md` 膨胀到数万字。patch 只记录变更，主文件按 patch 原地更新 |
| `global/worldview.md` 是当前有效状态 | 不是历史追加，而是当前真值。增删改都是原地操作，文件大小始终可控 |
| `chapters/index.jsonl` 作为状态机真源 | JSON Lines 格式：比 YAML 不易出错，比 Markdown 表格解析更稳，每章一行可追加写入 |
| `global/characters_index.md` 全局角色注册表 | 解决角色离场多章后"蒸发"问题，与章节快照互补 |
| `archive/` 定期归档 | 每 50 章归档 timeline/foreshadowing 已完结条目，控制主文件大小 |

---

## 三、能力模型与子命令

### 命令接口

```
pizhi init              # 初始化新项目
pizhi brainstorm        # 灵感模式（对话式头脑风暴）
pizhi outline expand    # 扩写大纲
pizhi write             # 单章扩写正文
pizhi continue          # 自动续写（大纲 + 正文批量）
pizhi compile           # 编译成品正文
pizhi review            # 一致性审查
pizhi status            # 项目进度、活跃伏笔、待写章节
```

### 模式 1：灵感模式（Brainstorm）

**触发**：`pizhi brainstorm` 或项目初期。

**流程**：多轮对话，引导用户提供核心点子，逐步展开。

**产出物**：
- `global/synopsis.md` — 故事总体简介
- `global/worldview.md` — 初始世界观
- `global/rules.md` — 写作规则（从模板生成，用户可深度定制）
- `global/foreshadowing.md` — 空的初始伏笔文件
- `global/outline_global.md` — 全书分卷大纲
- `ch000/characters.md` — 初始角色设定（`ch000` 是故事开始前的初始快照）
- `ch000/relationships.md` — 初始人物关系

### 模式 2：自动续写（Continue）

**触发**：`pizhi continue --count N [--direction "..."]`

**流程**：
1. 读取当前最新状态
2. 先调用大纲扩写逻辑，补充 N 章细纲
3. 逐章进入 Chapter Loop 生成正文
4. **每 3 章设一个检查点**，暂停向用户展示变更摘要，确认后继续
5. 全部完成后汇报各章标题、字数、关键剧情节点

**检查点内容**：
- 新章标题与 100 字摘要
- 人物/关系变更清单
- 新引入和回收的伏笔

### 模式 3：扩写大纲（Outline Expand）

**触发**：`pizhi outline expand --chapters N~M [--direction "..."]`

**流程**：
1. 读取 `global/` 下所有设定和最新快照
2. 生成目标章节的细纲（场景、冲突、转折、情绪节奏）
3. 更新 `outline_global.md` 和各章 `outline.md`
4. 不生成正文

### 模式 4：扩写正文（Write）

**触发**：`pizhi write --chapter N`

**流程**：执行标准 Chapter Loop（见第五节）。

### 辅助命令

- `pizhi compile`：将 `chapters/` 下已完成章节编译到 `manuscript/`
- `pizhi review`：执行单章或全书一致性审查
- `pizhi status`：读取 `chapters/index.jsonl` 生成项目进度报告

---

## 四、全局文件管理

### 4.1 世界观：Patch 模型

`global/worldview.md` 存储的是**当前有效世界观**，不是历史追加记录。每章创作后，如果世界观有变更，AI 输出一个 patch 并应用到主文件。

**每章的 `worldview_patch.md` 格式**（仅在变更时生成）：

```markdown
# 第 10 章世界观变更

## Added
- **码头三号仓**：位于葵涌货柜码头东区，表面是正规仓库，地下层用于走私中转。

## Modified
- **雷老板势力范围**：此前记载为"深水埗至旺角"；本章确认已扩展至湾仔部分地盘（通过收买当地茶餐厅网络）。

## Retracted
- （无）
```

**更新规则**：
- `Added` 条目追加到 `global/worldview.md` 对应分类下
- `Modified` 条目原地替换 `global/worldview.md` 中的已有条目。匹配方式为**粗体标题精确文本匹配**——patch 中的 `**雷老板势力范围**` 必须与 `worldview.md` 中的 `**雷老板势力范围**` 完全一致。若匹配不到任何条目，报错而非静默追加
- `Retracted` 条目从 `global/worldview.md` 中删除，同样使用粗体标题精确匹配
- 若无变更，不生成 `worldview_patch.md`，主文件不动
- 若匹配出现歧义（多个条目标题相同），说明 `worldview.md` 本身的条目标题不够具体，应在下次更新时重命名以消除歧义

这保证了 `global/worldview.md` 始终是当前真值，大小可控（不会无限追加）。

### 4.2 伏笔追踪器

`global/foreshadowing.md` 采用四级生命周期：

```markdown
# 伏笔追踪器

## Active（未回收）

### F001 | 优先级：高
- **描述**：沈轩在码头发现的血衣
- **埋设章节**：ch003
- **计划回收**：ch010-ch015
- **涉及角色**：沈轩, 阿坤
- **最后引用**：ch007

### F002 | 优先级：中
- **描述**：神秘电话中的潮州话暗号
- **埋设章节**：ch007
- **计划回收**：ch020-ch025
- **涉及角色**：沈轩
- **最后引用**：ch007

## Referenced（近期被引用但未回收，提醒 AI 保持呼应）

### F003 | 优先级：低
- **描述**：老周提到的二十年前大火
- **埋设章节**：ch002
- **计划回收**：ch030+
- **涉及角色**：老周
- **最后引用**：ch009（被老周再次提及但未展开）

## Resolved（已回收）

### F000
- **描述**：阿坤的失踪
- **埋设章节**：ch001
- **回收章节**：ch005
- **回收方式**：阿坤被雷老板扣押，在码头货仓被找到

## Abandoned（因剧情调整放弃）

### F099
- **描述**：最初设想的神秘组织线
- **埋设章节**：ch004
- **放弃章节**：ch010
- **放弃原因**：大纲调整，该组织线被合并到雷老板势力线中
```

**每章加载伏笔时的筛选逻辑**：

1. 全部 `Active` 伏笔按优先级排序加载
2. `Referenced` 中与本章出场角色相关的条目附带加载
3. `planned_payoff` 接近当前章节号（±5 章）的伏笔标注为「待回收提醒」
4. 高优先级伏笔即使预计回收章节较远，也保持加载

**`planned_payoff` 语法**：
- `ch018`：计划在单章回收
- `ch010-ch015`：计划在章节区间内回收
- `ch030+`：30 章后任意时点回收

实现层需要将其解析为 `start_chapter / end_chapter?`，供筛选逻辑和超期检查共用。

### 4.3 角色快照

每章的 `characters.md` 是该章结束时刻的**活跃角色**状态截面——仅包含本章出场或被直接提及的角色，不包含全角色：

```markdown
# 第 10 章角色状态

## 沈轩
- **位置**：香港，湾仔，富叔茶餐厅二楼
- **状态**：左手缠绷带，精神亢奋
- **持有资源**：
  - 现金约 28 万港币
  - 码头三号仓短期使用权
  - 旺角两间铺面的转让意向
- **已知情报**：雷老板与泰国线的关联、阿坤是警方线人
- **情绪**：既得利又不安，开始怀疑身边人的忠诚
- **未说出口**：手里有线人证据却不敢用——用了就暴露自己知道得太多

## 阿坤
- **位置**：香港，养和医院
- **状态**：重伤住院，意识清醒但虚弱
- **持有资源**：未知
- **已知情报**：自己的线人身份已暴露给沈轩
- **情绪**：恐惧，在赌沈轩不会杀自己
```

### 4.4 关系快照

每章的 `relationships.md` 记录本章结束时的关系状态和本章的变化：

```markdown
# 第 10 章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|-----|------|--------|------|
| 沈轩 | 阿坤 | 控制 + 威慑 | 低 | 掌握了线人把柄 |
| 沈轩 | 雷老板 | 独立 + 试探对抗 | 极低 | 表面仍维持从属 |
| 沈轩 | 旺角地头蛇 | 初步合作意向 | 中 | 利益交换尚未兑现 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 阿坤 | 利用 + 表面兄弟 | 控制 + 威慑 | 发现阿坤是线人 |
| 沈轩 → 雷老板 | 从属 + 观望 | 独立 + 试探对抗 | 码头血衣事件揭示背叛 |
```

### 4.5 全局角色注册表

`global/characters_index.md` 是跨章节的稳定角色身份索引，解决角色离场多章后回归时"蒸发"的问题：

```markdown
# 全局角色注册表

## 沈轩
- **标准名**：沈轩
- **别名**：轩哥、小沈
- **身份**：从内地来港的年轻人，逐步进入灰色地带
- **核心动机**：生存与利益最大化
- **首次出场**：ch001
- **最近出场**：ch010
- **长期属性**：极致利己，讲收益讲底线，非无脑疯狗
- **未解决关系**：与雷老板的从属正在瓦解、阿坤的线人把柄尚未动用

## 阿坤
- **标准名**：阿坤
- **别名**：坤叔
- **身份**：沈轩的兄弟，实际是警方线人
- **核心动机**：在夹缝中求生
- **首次出场**：ch001
- **最近出场**：ch010
- **长期属性**：重情义但被胁迫
- **未解决关系**：线人身份暴露后与沈轩的控制关系
```

**每章更新规则**：
- 本章出场的角色，更新"最近出场"字段
- 角色的长期属性发生变化时（如身份转变），原地更新
- 新角色首次出场时，追加新条目

**输入加载规则**：
- Chapter Loop 输入加载时，除了上章 `characters.md` 的活跃角色，还需从 `characters_index.md` 检索本章大纲涉及但近期未出场的角色
- 检索方式：匹配大纲中的角色名（含别名）→ 加载对应条目

**文件大小估算**：每条角色记录约 100-200 字，20 个角色约 2000-4000 字，完全在上下文预算内。

### 4.6 章节索引（状态机）

`chapters/index.jsonl` 是机器可读的章节状态真源，采用 JSON Lines 格式（每章一行 JSON 对象）：

```
{"n":1,"title":"雨夜访客","vol":1,"status":"drafted","summary":"沈轩雨夜抵达码头，意外发现血衣","updated":"2026-04-15"}
{"n":2,"title":"码头血衣","vol":1,"status":"outlined","summary":"","updated":"2026-04-15"}
```

**字段说明**：
- `n`：章节号（整数）
- `title`：章节标题
- `vol`：卷号
- `status`：状态枚举（`planned` → `outlined` → `drafted` → `reviewed` → `compiled`）
- `summary`：100 字以内的章节摘要（仅 drafted 后填写）
- `updated`：最后更新日期

**更新时机**：
- `pizhi outline expand`：写入/更新为 `planned` 或 `outlined`
- `pizhi write`：更新为 `drafted`，填写 title 和 summary
- `pizhi review`：更新为 `reviewed`
- `pizhi compile`：更新为 `compiled`

**与 `outline_global.md` 的关系**：`outline_global.md` 降级为"人类可读的全书叙事蓝图"，不再承载状态追踪。所有状态查询（`pizhi status`、`pizhi continue`）通过 `index.jsonl` 驱动。

### 4.7 时间线

`global/timeline.md` 记录结构化时间线事件，供单调性检查、重大转折回顾和 synopsis 覆盖性检查使用：

```markdown
# 时间线

## T010-01
- **时间**：1986-03-14 夜
- **事件**：沈轩带人去码头三号仓
- **闪回**：否
- **重大转折**：否

## T010-02
- **时间**：1986-03-15 凌晨
- **事件**：发现血衣，与雷老板手下短暂冲突
- **闪回**：否
- **重大转折**：是
```

**规则**：
- 每个事件都必须显式声明是否为闪回、是否为重大转折
- `at` 字段必须使用可排序格式：优先 `YYYY-MM-DD HH:MM`；若只写时段，则使用 `YYYY-MM-DD <时段>`，其中 `<时段>` 仅允许 `凌晨 / 早晨 / 上午 / 中午 / 下午 / 傍晚 / 夜`
- A 类检查中的时间线单调性只对 `闪回 = 否` 的事件做顺序校验
- synopsis 覆盖性检查只要求覆盖 `重大转折 = 是` 的事件

---

## 五、Chapter Loop（自回归核心）

每章创作都是一次独立的输入-处理-输出运算，不依赖上下文传递。

### 5.1 输入协议

| # | 输入项 | 来源 | 加载时机 | 典型大小 |
|---|--------|------|---------|---------|
| 1 | 故事简介 | `global/synopsis.md` | 必读 | 500-1000 字 |
| 2 | 当前世界观 | `global/worldview.md` | 必读 | 1000-2500 字 |
| 3 | 写作规则 | `global/rules.md` | 必读 | 800-1500 字 |
| 4 | 活跃伏笔 | `global/foreshadowing.md`（active + relevant referenced） | 必读 | 500-2000 字 |
| 5 | 本章大纲 | `chXXX/outline.md` | 必读 | 200-500 字 |
| 6 | 上章正文 | `ch(X-1)/text.md` | 必读 | 3000-5000 字 |
| 7 | 上章角色状态 | `ch(X-1)/characters.md` | 必读 | 500-1000 字 |
| 8 | 上章关系状态 | `ch(X-1)/relationships.md` | 必读 | 300-800 字 |
| 9 | 角色注册表 | `global/characters_index.md`（大纲涉及但近期未出场角色） | 按需 | 200-800 字/角色 |
| 10 | 前前章正文 | `ch(X-2)/text.md` | 按需 | 3000-5000 字 |

**典型输入总量**：
- 最小（无远期角色、无前前章）：7300-13800 字
- 含远期角色 + 前前章：11000-20000 字
- 远期（100+ 章，世界观和伏笔更丰满）：15000-25000 字

这是对项目初期 3000-8000 字估算的修正。中期以后输入量会显著增长，需要通过世界观的 patch 模型和伏笔的筛选逻辑来控制上限。

### 5.2 输出 Schema

AI 的输出必须遵循以下格式，由解析规则自动拆分到对应文件：

```
---
chapter_title: "第十章 雨夜访客"
word_count_estimated: 3200
characters_involved: ["沈轩", "阿坤", "雷老板"]
worldview_changed: true
synopsis_changed: false
timeline_events:
  - at: "1986-03-14 夜"
    event: "沈轩带人去码头三号仓"
    is_flashback: false
    is_major_turning_point: false
  - at: "1986-03-15 凌晨"
    event: "发现血衣，与雷老板手下短暂冲突"
    is_flashback: false
    is_major_turning_point: true
  - at: "1986-03-15 上午"
    event: "去医院看阿坤，发现线人证据"
    is_flashback: false
    is_major_turning_point: true
  - at: "1986-03-15 下午"
    event: "在茶餐厅与旺角地头蛇谈铺面转让"
    is_flashback: false
    is_major_turning_point: false
foreshadowing:
  introduced:
    - id: F005
      desc: "沈轩在阿坤床底发现半张照片"
      planned_payoff: "ch018"
      priority: medium
      related_characters: ["沈轩"]
  referenced:
    - id: F003
  resolved:
    - id: F001
      resolution: "血衣是雷老板故意放的"
---

（正文内容，标准 Markdown）

---

## characters_snapshot

（角色状态快照，格式见 4.3 节）

## relationships_snapshot

（关系状态快照，格式见 4.4 节）

## worldview_patch

（仅在 worldview_changed 为 true 时存在，格式见 4.1 节）

## synopsis_new

（仅在 synopsis_changed 为 true 时存在。完整的新的 synopsis.md 内容。
先写入 synopsis_candidate.md，校验通过后再替换 synopsis.md——防止长期记忆被悄悄擦除。）
```

### 5.3 解析规则

1. **YAML frontmatter**：第一个 `---` 之间的内容，提取元数据和伏笔更新指令
2. **正文**：frontmatter 之后、`## characters_snapshot` 之前的内容 → 写入 `chXXX/text.md`
3. **角色快照**：`## characters_snapshot` 到 `## relationships_snapshot` 之间的内容 → 写入 `chXXX/characters.md`
4. **关系快照**：`## relationships_snapshot` 到 `## worldview_patch`（或 `## synopsis_new` 或文件末尾）之间的内容 → 写入 `chXXX/relationships.md`
5. **世界观 patch**：若 `worldview_changed: true`，读取 `## worldview_patch` 区块 → 写入 `chXXX/worldview_patch.md`，同时应用 patch 到 `global/worldview.md`
6. **Synopsis 更新**：若 `synopsis_changed: true`，读取 `## synopsis_new` 区块的完整内容 → 先写入 `global/synopsis_candidate.md`，执行覆盖性检查（见 7.2 节），通过后替换 `global/synopsis.md` 并删除 candidate；未通过则保留 candidate 并写入 `notes.md` 告警
7. **伏笔更新**：根据 frontmatter 中的 `foreshadowing.introduced / referenced / resolved` 更新 `global/foreshadowing.md`
8. **时间线更新**：直接读取 frontmatter 中的 `timeline_events` 结构化数组 → 以“时间 / 事件 / 闪回 / 重大转折”的格式追加到 `global/timeline.md`

### 5.4 清理与衔接

每章完成后：
1. 持久化所有输出到文件
2. 不在上下文中保留本章正文和快照
3. 下一章的输入完全由文件系统驱动
4. 更新 `cache/last_session.md` 记录进度

---

## 六、记忆系统

参考论文 *Beyond a Million Tokens* 的三层记忆架构，适配文件系统：

### 6.1 长期情景记忆

| 属性 | 说明 |
|------|------|
| **载体** | `global/synopsis.md` + `global/timeline.md` |
| **作用** | 跨越全书的核心事实、重大事件、人物命运转折 |
| **更新频率** | 每章评估，仅在有重大转折时更新 synopsis；timeline 每章追加结构化事件 |
| **访问方式** | 每章必读 synopsis（控制在 1000 字内）；timeline 按需加载近 20 章条目（保留闪回/重大转折标记） |

### 6.2 短期工作记忆

| 属性 | 说明 |
|------|------|
| **载体** | 最近 1-2 章的 `text.md` + `characters.md` + `relationships.md` |
| **作用** | 叙事连贯性——语气衔接、场景延续、对话呼应 |
| **更新频率** | 每章滑动窗口（固定只保留最近 2 章） |
| **访问方式** | 每章必读，全文加载 |

### 6.3 累积事实库

| 属性 | 说明 |
|------|------|
| **载体** | `global/worldview.md`（当前有效状态）+ 各章 `worldview_patch.md`（历史变更） |
| **作用** | 世界设定细节、人物能力边界、势力版图等结构化事实 |
| **更新频率** | 每章按 patch 增删改，主文件原地更新 |
| **访问方式** | 每章必读主文件（当前有效状态，大小可控）；历史 patch 按需查阅 |

### 6.4 伏笔缓冲区

| 属性 | 说明 |
|------|------|
| **载体** | `global/foreshadowing.md` |
| **作用** | 追踪所有伏笔的生命周期，防止遗忘或烂尾 |
| **更新频率** | 每章更新（introduced / referenced / resolved / abandoned） |
| **访问方式** | 每章加载 active + 相关 referenced（经筛选逻辑过滤） |

### 6.5 角色身份库

| 属性 | 说明 |
|------|------|
| **载体** | `global/characters_index.md` |
| **作用** | 维护所有角色的稳定身份（标准名、别名）、长期属性和未解决关系 |
| **更新频率** | 每章更新出场角色的最近出场、长期属性变化；新角色首次追加 |
| **访问方式** | 按需检索——匹配本章大纲涉及但近期未出场的角色，加载其长期属性 |

---

## 七、一致性保障

参考论文 *Lost in Stories* 的 ConStory-Bench 分类体系，采用 **A/B 两层检查**：

### 7.1 A 类：结构约束（脚本可校验）

以下检查可以用简单脚本自动完成，不需要 AI 参与：

| 检查项 | 校验方式 |
|--------|---------|
| 伏笔 ID 引用合法性 | `resolved` 中引用的 ID 必须存在于 `active` 或 `referenced` 中 |
| 章节号连续性 | 新生成章节号 = 上一章号 + 1 |
| 出场角色一致性 | frontmatter 中 `characters_involved` 列出的角色必须在正文中有台词或行动 |
| 时间线单调性 | frontmatter 中 `timeline_events` 里 `is_flashback = false` 的事件时间不能早于上一章最后一个非闪回事件 |
| 文件完整性 | 解析后每个必要文件（text, characters, relationships）都有内容 |

### 7.2 B 类：语义推理（AI 审查）

以下检查由 AI 在 post_chapter 钩子中执行：

| 类别 | 检查内容 |
|------|---------|
| **人物一致性** | 性格、动机、能力是否与上一章快照矛盾 |
| **时间线合理性** | 时间跨度是否合理（不能一天内横跨三个城市做五件大事） |
| **世界设定一致性** | 地点、规则、物品、制度是否与 worldview.md 矛盾 |
| **因果一致性** | 事件的结果是否有充足的前因支撑（禁止机械降神） |
| **资源一致性** | 金钱、物品、人脉的获取与消耗是否与前文铺垫一致 |
| **Synopsis 覆盖性** | （仅在 `synopsis_changed: true` 时）新 synopsis 是否覆盖当前所有 active foreshadowing 涉及的主线、timeline 中标记为重大转折的事件。未覆盖则告警并暂停替换 |

### 7.3 检查输出格式

所有问题以统一格式输出到 `chXXX/notes.md`：

```markdown
## 一致性检查结果

### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩在第 9 章明确不知道泰国线的存在，但第 10 章正文中他对雷老板说"你泰国那边的事我都知道"
- **证据**：ch009/characters.md 中沈轩的 known_intelligence 不含泰国线
- **建议修法**：改为沈轩通过暗示试探，而非直接声称知道
```

### 7.4 全书级审查

`pizhi review --full` 触发更深层检查：

1. **跨章矛盾扫描**：串联所有快照中的角色状态变化，查找跳跃或矛盾
2. **伏笔完整性**：标记超过 `planned_payoff` 范围仍未回收的伏笔
3. **人物弧线验证**：检查主要人物的动机和性格变化是否有叙事支撑
4. **时间线审计**：串联全部 timeline 条目，查找断裂或矛盾

---

## 八、配置与初始化

### 8.1 `pizhi init` 交互流程

```
$ pizhi init

辟芷 — AI 协同写作工具
========================

? 小说名称：______
? 类型/风格（如：港综商战、都市异能、历史权谋）：______
? 预计总章数范围（如：200-300）：______
? 分卷策略（每卷章数，默认 20）：______
? 视角与叙事风格：______

正在创建项目框架...
✓ .pizhi/ 已创建
✓ 全局配置已初始化
✓ ch000/ 初始快照目录已创建
✓ manuscript/ 已创建

接下来你可以：
  1. pizhi brainstorm — 开始灵感模式
  2. 或手动编辑 .pizhi/global/ 下的文件
```

### 8.2 config.yaml

```yaml
project:
  name: "小说名称"
  genre: "港综商战"
  pov: "第三人称有限视角"
  created: "2026-04-14"
  last_updated: "2026-04-14"

chapters:
  total_planned: 260
  per_volume: 20

generation:
  context_window:
    prev_chapters: 2
    max_outline_words: 500
    max_chapter_words: 5000
  style:
    tone: "冷峻含蓄，重氛围轻说教"
    dialogue_ratio: 0.35

consistency:
  auto_check: true
  checkpoint_interval: 3        # 自动续写时每 N 章暂停一次

foreshadowing:
  auto_archive_resolved: true
  reminder_threshold: 5         # 计划 N 章内回收的伏笔提前标注
```

说明：章节进度不在 `config.yaml` 中重复维护，唯一状态真源为 `.pizhi/chapters/index.jsonl`。

### 8.3 rules.md 模板

`rules.md` 承载项目特有的写作规则，灵感模式下从模板生成，用户可深度定制。模板包含：

- 主角行为铁律
- 类型边界（如：智斗高于武斗，不写系统保姆化）
- 叙事原则（Show don't tell，用场景和物件推进，不用背景讲解）
- 配角要求（必须有独立动机和反扑能力）
- 负面清单（禁止的行为模式）

迁移现有 noval skill 时，「项目核心宪法」直接迁入此文件。

---

## 九、编译与输出

`manuscript/` 目录是用户可见的成品，从 `chapters/` 编译而来。

**编译策略**：
- 每卷完成时自动编译（第 20、40、60... 章完成后触发）
- 用户可随时手动触发 `pizhi compile`；`pizhi status` 仅显示当前编译状态
- 编译方式：按卷拼接各章 `text.md`，添加卷标题和分隔符

### 9.1 归档规则

每完成 50 章时，在 `pizhi continue` 的检查点或 `pizhi review --full` 时自动触发归档：

**伏笔归档**：
- 将 `foreshadowing.md` 中 Resolved/Abandoned 超过 30 章的条目移入 `archive/foreshadowing_chXXX-YYY.md`
- 原文件中删除已归档条目

**时间线归档**：
- 将 `timeline.md` 中 50 章以前的条目移入 `archive/timeline_chXXX-YYY.md`
- 原文件只保留近 50 章的条目

**归档文件规则**：
- 存放在 `.pizhi/archive/` 目录下，按章节范围命名
- 不进入常规输入加载，只在 `review --full` 时按需查阅
- A 类检查脚本增加归档文件完整性校验

---

## 十、与现有 noval skill 的关系

| 维度 | noval（现有） | 辟芷（新） |
|------|--------------|-----------|
| 定位 | 面向特定小说的定制技能 | 通用化长篇写作框架 |
| 适用 | 单一项目，硬编码主角名、类型 | 任何项目，通过 config.yaml + rules.md 配置 |
| 元数据 | 扁平文件（task_plan, findings, progress） | 分层结构（全局 + 每章快照） |
| 一致性 | 依赖作者经验和 AI 判断 | A/B 两层结构化检查 |
| 自回归 | 无显式协议 | 每章严格输入-输出协议 |
| 世界观 | 手动维护 character_relationships.md | 自动 patch + 每章快照 |

**迁移路径**：
- `character_relationships.md` → 拆分为各章 `relationships.md` + `characters.md`
- `task_plan.md` / `findings.md` / `progress.md` → 迁入 `cache/` + `rules.md`
- 「项目核心宪法」→ 直接迁入 `rules.md`
- 正文分卷文件 → 拆为各章 `text.md`，原文件保留在 `manuscript/`

---

## 十一、参考论文取舍

### Beyond a Million Tokens — 三层记忆

**采纳**：长期情景 → synopsis + timeline；短期工作 → 最近章节正文 + 快照；累积事实 → worldview + patch。

**不采纳**：临时记忆库。单 Agent 文件系统场景下，用 foreshadowing.md 的 active/referenced 分类替代。

### Lost in Stories — 一致性检查

**采纳**：错误分类体系和「问题→证据→修法」输出格式。A/B 两层检查设计。

**不采纳**：独立的 ConStory-Checker 管道。简化为 post_chapter 钩子内的自检流程。

### StoryBox — 多智能体沙盒

**暂不采纳**：单 Agent 架构下实现成本过高，且与人机协同的定位有张力。预留为 v2.0+ 方向。

---

## 十二、设计决策溯源

以下记录关键决策来自哪份设计或评审，便于未来回溯：

| 决策 | 来源 | 理由 |
|------|------|------|
| `.pizhi/` + `manuscript/` 分离 | GLM 原设计 | 双方评审均认可，用户心智模型好 |
| 每章自包含目录 | GLM 原设计 | Kimi 评审指出其正文与元数据分离的审阅问题 |
| 快照按类型拆分文件 | Kimi 原设计 + Kimi 评审 GLM | 兼得自包含和可独立加载 |
| Worldview patch 模型 | Kimi 原设计 | Kimi 评审指出 GLM 追加式更新的膨胀风险 |
| 伏笔四级生命周期 | Kimi 原设计 | referenced 状态防止远期伏笔被遗忘 |
| 伏笔筛选逻辑 | Kimi 原设计 | 比全量加载更高效 |
| YAML frontmatter 输出 Schema | Kimi 原设计 | 可自动化解析，格式稳定
| 子命令接口 | Kimi 原设计 | GLM 评审认可其完整性 |
| rules.md 承载写作约束 | GLM 原设计 | Kimi 设计中 [style] 段过于粗略 |
| A/B 两层一致性检查 | Kimi 评审 GLM | 结构约束脚本做，语义推理 AI 做，比纯 AI 自检可靠 |
| 自动续写 3 章检查点 | Kimi 评审 GLM | 防止批量生成后方向偏离 |
| 上下文估算修正 | Kimi 评审 GLM | 原估算 3000-8000 字过于乐观，修正为 7000-25000 字 |
| 5 大类检查 + 输出格式 | GLM 原设计 | Kimi 评审中一致性检查只有 3 类且无输出格式 |
| noval skill 迁移路径 | GLM 原设计 | Kimi 未讨论 |
| synopsis 整体替换而非 patch | GLM 回应 Kimi 终稿评审 | synopsis 仅 500-1000 字，整体替换比 diff 更简单可靠 |
| timeline_events 结构化输出 | Kimi 终稿评审 | AI 显式申报时间线事件，比脚本 NLP 提取准确，也支持 A 类单调性校验 |
| worldview 粗体标题精确匹配 | GLM 回应 Kimi 终稿评审 | 拒绝 [identifier] 语法以保持人类可读性，用粗体标题精确文本匹配消除歧义 |
| ch000/ 初始快照目录 | Kimi 终稿评审 | 修复目录树示例遗漏 |
| 章节索引用 JSON Lines | OpenAI 评审 + GLM 裁定 | 比 YAML 不易出错（无缩进陷阱），比 Markdown 表格解析更稳（无对齐/分隔符问题），每章一行可追加写入 |
| 全局角色注册表 characters_index | OpenAI 评审 | 解决角色离场多章后"蒸发"问题，章节快照只保留活跃角色，注册表维护长期身份 |
| synopsis candidate 先校验后替换 | OpenAI 评审 | synopsis 是长期记忆核心，先污染后告警会导致下一章基于错误数据生成 |
| timeline/foreshadowing 归档规则 | OpenAI 评审 | 每 50 章归档已完结条目，从开放问题收束为实施规则 |

---

## 十三、开放问题

1. **快照格式**：当前定义为 Markdown。是否在某些字段引入 YAML 以提升程序解析稳定性？
2. **多模型配置**：是否允许灵感模式用强模型、正文扩写用快模型？
3. **版本控制**：~~是否推荐用户纳入版本管理？~~ **已决定**：推荐。`.pizhi/` 全部是文本文件，天然支持 Git。`pizhi init` 完成后建议 `git init`。
4. **多 Agent 扩展**：是否预留审稿 Agent / 考据 Agent 的接口？
5. **manuscript 编译粒度**：当前按卷编译。是否支持按章、按自定义范围编译？
6. **超长篇压缩**：~~是否需要定期归档到 `archive/` 目录？~~ **已决定**：每 50 章归档。见 9.1 节归档规则。

---

*本文档融合 GLM 设计、Kimi 设计、双向评审意见及 OpenAI 评审，作为辟芷技能的实现基线。*
