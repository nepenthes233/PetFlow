# PetFlow 项目设计 Plan  
## 基于任务图的桌宠 Agent 工作流管理器

> 状态说明：本文档是早期创意池和完整功能设想，保留用于查阅产品想法。当前项目的正式技术方案已经调整为 Python + Tkinter + Canvas，具体实现规范以 `docs/PetFlow 动态日历功能设计.md`、`docs/architecture.md` 和 `docs/development.md` 为准。本文中出现的 Qt、QGraphicsView、C++ 类结构仅作为历史设计参考，不作为当前开发约束。

---

## 0. 项目一句话定位

**PetFlow 是一个用“任务图”代替传统日历/todo-list 的桌宠式个人工作流管理器。**

用户可以把项目、routine、习惯、资源、奖励等内容组织成一张有向图。桌宠 Agent 会在图上游走，根据节点状态、边关系、时间和用户行为，帮助用户推荐下一步、拆分任务、提醒 routine、总结进度。

---

# 1. 项目核心亮点

本项目不做传统日历式日程管理，而是把任务组织成图结构。

核心创新点：

1. **任务图作为主交互界面**
   - 节点表示任务、习惯、资源、奖励、检查点等。
   - 边表示依赖、循环、推荐、触发等关系。
   - 图可以有环，适合表达 routine 和工作流。

2. **桌宠不只是装饰，而是图上的 Agent**
   - 桌宠可以移动到某个节点旁边。
   - 完成节点后，桌宠沿边推荐下一个节点。
   - routine 到期后，桌宠主动提醒。
   - 用户摸鱼或停滞时，桌宠吐槽/建议。

3. **轻量 Agent 系统**
   - 根据自然语言目标生成任务图。
   - 对单个节点进行智能拆分。
   - 根据当前图状态推荐下一步。
   - 对一天/一周的任务进展生成复盘。

4. **系统能力扩展**
   - 剪贴板内容变成资源节点。
   - 前台窗口检测用于专注/摸鱼监督。
   - 文件或链接可以挂载到节点。

---

# 2. 推荐项目名称

可以从下面选：

- **PetFlow**
- **TaskGraph Agent**
- **FlowPet**
- **GraphTodo Pet**
- **DeadlinePet Graph**
- **MindPet**

我个人最推荐：

> **PetFlow：基于任务图的桌宠 Agent 工作流管理器**

---

# 3. 用户使用场景

## 场景一：规划 Qt 大作业

用户输入：

```text
我想两周内完成一个 Qt 大作业，主题是桌宠任务图 Agent，需要图编辑、桌宠、LLM 拆任务、演示视频。
```

Agent 自动生成任务图：

```text
确定需求 -> 设计数据结构 -> 实现图编辑
                         -> 实现桌宠
                         -> 实现 Agent
实现图编辑 + 实现桌宠 + 实现 Agent -> UI 美化 -> 录制演示视频 -> 写报告
```

---

## 场景二：routine 环

用户创建 routine：

```text
写代码 -> 测试 -> 记录 bug -> 修复 bug -> 写代码
```

这个环表示持续迭代的开发流程。

每完成一个节点，桌宠会跳到下一个节点旁边，说：

```text
下一步该测试啦，要不要开始 25 分钟专注？
```

---

## 场景三：节点智能拆分

用户右键点击：

```text
实现图视图
```

选择：

```text
让 Agent 拆分该节点
```

Agent 生成子任务：

```text
创建 QGraphicsScene
实现 NodeItem
实现 EdgeItem
实现节点拖拽
实现右键菜单
保存节点坐标
```

用户确认后，系统自动创建子图。

---

## 场景四：桌宠监督摸鱼

当前任务节点是：

```text
实现 EdgeItem
```

用户打开 B 站。

桌宠检测到当前前台窗口后提示：

```text
你现在应该在「实现 EdgeItem」节点，但我发现你离开战场了。
要把这 10 分钟记录为休息节点，还是回到任务？
```

---

# 4. 功能范围总览

建议把功能分成四层：

```text
第一层：任务图核心
第二层：桌宠交互
第三层：Agent 能力
第四层：系统增强能力
```

---

# 5. 第一层：任务图核心功能

这是项目最重要的基础。

## 5.1 图编辑主界面

主界面是一张可视化任务图。

需要支持：

- 创建节点
- 删除节点
- 编辑节点
- 拖动节点
- 创建边
- 删除边
- 保存图
- 加载图
- 缩放视图
- 平移视图
- 右键菜单
- 节点状态显示

建议用 Qt Widgets 实现：

- `QGraphicsView`
- `QGraphicsScene`
- 自定义 `NodeItem`
- 自定义 `EdgeItem`

---

## 5.2 节点类型设计

节点不只是 todo，而是多种类型。

### 1. Task 节点

表示一次性任务。

例如：

```text
实现图视图
写 README
录制演示视频
```

字段：

```json
{
  "id": "node_001",
  "type": "task",
  "title": "实现图视图",
  "description": "使用 QGraphicsView 实现节点和边的展示",
  "status": "todo",
  "priority": 4,
  "estimatedMinutes": 120,
  "actualMinutes": 0,
  "createdAt": "...",
  "updatedAt": "...",
  "completedAt": null,
  "x": 100,
  "y": 200,
  "tags": ["Qt", "核心功能"],
  "attachments": []
}
```

---

### 2. Routine 节点

表示周期性任务或习惯。

例如：

```text
每天背单词
每周复盘
每月整理桌面
```

字段：

```json
{
  "id": "node_002",
  "type": "routine",
  "title": "每晚复盘",
  "status": "todo",
  "repeatType": "daily",
  "repeatDays": [],
  "repeatInterval": 1,
  "lastCompletedAt": null,
  "nextDueAt": "...",
  "streak": 0
}
```

支持的重复类型建议先做：

```text
none
daily
weekly
monthly
```

MVP 阶段可以只做：

```text
daily / weekly
```

---

### 3. Resource 节点

表示资源，不一定需要完成。

例如：

```text
Qt 官方文档
课程 PPT
参考 GitHub 仓库
一段剪贴板代码
论文 PDF
```

字段：

```json
{
  "id": "node_003",
  "type": "resource",
  "title": "QGraphicsView 文档",
  "description": "Qt 官方图形视图框架文档",
  "resourceType": "url",
  "resourcePath": "https://doc.qt.io/qt-6/graphicsview.html"
}
```

资源类型：

```text
url
file
text
image
code
```

---

### 4. Checkpoint 节点

表示检查点、复盘点、提交前检查。

例如：

```text
提交前检查
演示视频检查
每周复盘
```

点击 checkpoint 节点时，可以显示 checklist。

字段：

```json
{
  "id": "node_004",
  "type": "checkpoint",
  "title": "提交前检查",
  "checklist": [
    {"text": "程序能正常启动", "checked": false},
    {"text": "数据能保存和加载", "checked": false},
    {"text": "演示视频已录制", "checked": false}
  ]
}
```

---

### 5. Reward 节点

表示奖励或休息。

例如：

```text
看一集番
刷 B 站 15 分钟
出门觅食
打一把游戏
```

字段：

```json
{
  "id": "node_005",
  "type": "reward",
  "title": "刷 B 站 15 分钟",
  "unlockCondition": "complete_2_tasks",
  "durationMinutes": 15,
  "locked": true
}
```

MVP 阶段可以不做复杂解锁，只保留节点类型和特殊样式。

---

## 5.3 节点状态设计

节点状态：

```text
todo       未开始
doing      进行中
done       已完成
blocked    被阻塞
paused     暂停
```

建议颜色：

```text
todo       灰/蓝
doing      黄色
done       绿色
blocked    红色
paused     紫色
resource   青色
reward     粉色
```

---

## 5.4 边类型设计

边也需要有语义。

### 1. Dependency 边

表示依赖关系。

```text
A -> B
```

含义：

```text
完成 A 后才能开始 B
```

dependency 边原则上不应该形成环。

---

### 2. Routine 边

表示 routine 循环。

```text
写代码 -> 测试 -> 修 bug -> 写代码
```

routine 边允许形成环。

---

### 3. Recommendation 边

表示推荐路径。

```text
写代码卡住 -> 看文档
写代码卡住 -> 问 Agent
```

允许形成环。

---

### 4. Trigger 边

表示触发关系。

```text
完成代码 -> 提醒写 README
```

完成源节点后，系统自动提醒目标节点。

---

## 5.5 关于“图可以有环”的设计原则

系统不是完全禁止环，而是：

```text
dependency 边：不允许形成环
routine 边：允许形成环
recommendation 边：允许形成环
trigger 边：可以允许，也可以警告
```

这样逻辑上更合理。

例如：

```text
写代码 -> 测试 -> 修 bug -> 写代码
```

这是 routine/workflow loop，不是依赖矛盾。

但是：

```text
设计数据结构 depends on 实现图视图
实现图视图 depends on 设计数据结构
```

这是依赖循环，应该禁止。

---

## 5.6 图操作功能

### 节点操作

右键节点菜单：

```text
编辑节点
标记为进行中
标记为完成
添加子节点
让 Agent 拆分
添加附件
复制节点
删除节点
```

### 边操作

右键边菜单：

```text
修改边类型
删除边
```

### 空白区域右键菜单

```text
新建任务节点
新建 routine 节点
新建资源节点
新建 checkpoint 节点
新建 reward 节点
让 Agent 从目标生成任务图
自动布局
保存图
```

---

# 6. 第二层：桌宠交互设计

桌宠是项目的视觉亮点。

## 6.1 两种桌宠形态

建议设计两种形态：

### 1. 图内桌宠

在主界面打开时，桌宠是任务图上的一个 `PetItem`。

它可以：

- 移动到推荐节点旁边
- 在当前任务节点旁边待机
- 完成任务后沿边移动到下一个节点
- routine 到期后跑到 routine 节点
- 在节点旁边弹气泡

### 2. 桌面悬浮桌宠

主窗口最小化或隐藏时，桌宠悬浮在桌面上。

它可以：

- 显示当前任务
- 提醒 routine
- 监督摸鱼
- 点击后打开主窗口
- 弹出 Agent 对话框

如果时间不够，MVP 先做图内桌宠，后续再做桌面悬浮桌宠。

---

## 6.2 桌宠基础动作

建议做几个简单状态：

```text
idle      待机
walk      移动
happy     完成任务后开心
angry     摸鱼提醒
sleep     无任务或夜间
thinking  Agent 正在思考
```

实现方式：

- 简单版：不同 PNG 表情。
- 中等版：GIF 动画。
- 高级版：序列帧动画。

推荐：

> 用 GIF 或几张 PNG 切换即可，不要把美术成本做太高。

---

## 6.3 桌宠触发事件

桌宠需要响应这些事件：

```text
节点被完成
节点开始进行
routine 到期
Agent 推荐下一步
用户长时间无操作
检测到摸鱼窗口
LLM 请求正在处理
LLM 返回结果
```

对应行为：

| 事件 | 桌宠行为 |
|---|---|
| 完成节点 | 跳一下/开心，移动到下一个推荐节点 |
| routine 到期 | 跑到 routine 节点，气泡提醒 |
| 用户摸鱼 | 生气表情，弹出吐槽 |
| Agent 思考 | thinking 动画 |
| 推荐下一步 | 移动到推荐节点 |
| 无任务 | 睡觉 |

---

# 7. 第三层：Agent 功能设计

Agent 是项目高级感来源，但要做轻量、可控。

建议 Agent 分为：

```text
本地规则 Agent
LLM Agent
```

本地规则负责稳定逻辑，LLM 负责自然语言和规划生成。

---

## 7.1 Agent 功能一：自然语言生成任务图

### 功能描述

用户输入一个目标，Agent 自动生成节点和边。

例如：

```text
我想一周内做完一个 Qt 桌宠任务图项目。
```

Agent 生成：

```text
需求分析
设计数据结构
实现图编辑
实现桌宠
实现 Agent API
测试
录视频
写报告
```

并建立依赖关系。

### 交互流程

```text
用户输入目标
    ↓
程序构造 prompt
    ↓
调用 LLM
    ↓
LLM 返回 JSON
    ↓
程序校验 JSON
    ↓
显示预览
    ↓
用户确认
    ↓
导入任务图
```

### LLM 输出格式

```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "task",
      "title": "需求分析",
      "description": "明确项目功能范围",
      "priority": 4,
      "estimatedMinutes": 60
    },
    {
      "id": "n2",
      "type": "task",
      "title": "设计数据结构",
      "description": "设计节点、边和图存储格式",
      "priority": 5,
      "estimatedMinutes": 90
    }
  ],
  "edges": [
    {
      "from": "n1",
      "to": "n2",
      "type": "dependency"
    }
  ]
}
```

---

## 7.2 Agent 功能二：节点智能拆分

### 功能描述

用户选中一个较大的节点，Agent 将其拆成多个子节点。

例如：

```text
实现桌宠系统
```

拆成：

```text
实现透明窗口
加载桌宠动画
支持鼠标拖动
实现气泡提示
实现状态切换
```

### 交互流程

```text
右键节点
    ↓
选择“让 Agent 拆分”
    ↓
发送当前节点信息和上下文
    ↓
LLM 返回子节点和边
    ↓
用户确认
    ↓
原节点可以变成父节点/检查点，子节点加入图
```

### 推荐处理方式

不要直接删除原节点。

可以选择：

1. 原节点保留，作为父节点。
2. 子节点围绕原节点生成。
3. 原节点状态改为 `blocked` 或 `doing`。
4. 子节点全部完成后，原节点自动可完成。

---

## 7.3 Agent 功能三：推荐下一步

### 功能描述

用户点击：

```text
我现在该做什么？
```

Agent 根据图状态推荐一个节点。

输入考虑：

- 节点优先级
- 节点状态
- dependency 是否完成
- routine 是否到期
- 是否长期未触碰
- 预计耗时
- 当前时间
- 用户最近行为

### 推荐方式

建议采用：

```text
本地评分 + LLM 解释
```

本地规则先选出候选节点，LLM 负责生成自然语言理由。

### 本地评分示例

```text
score =
  priority * 10
+ dueSoonBonus
+ routineDueBonus
+ dependencyReadyBonus
+ staleBonus
- blockedPenalty
- tooLongPenalty
```

伪代码：

```cpp
int RecommendationEngine::scoreNode(const Node& node) {
    if (node.status == Done) return -9999;
    if (isBlocked(node)) return -1000;

    int score = 0;
    score += node.priority * 10;

    if (isRoutineDue(node)) score += 50;
    if (isDeadlineSoon(node)) score += 40;
    if (isDependencyReady(node)) score += 20;
    if (isStale(node)) score += 15;

    if (node.estimatedMinutes > 120) score -= 10;

    return score;
}
```

### 输出示例

```json
{
  "message": "我建议你现在做「实现 NodeItem」。它是图编辑功能的核心，而且前置任务已经完成，预计 40 分钟可以推进一版。",
  "recommendedNodeId": "node_123",
  "reasons": [
    "它的前置节点已经完成",
    "它属于核心功能",
    "它会阻塞后续 EdgeItem 的开发"
  ],
  "suggestedActions": [
    {
      "tool": "start_focus_timer",
      "args": {
        "minutes": 25
      }
    }
  ]
}
```

---

## 7.4 Agent 功能四：每日/每周复盘

### 功能描述

Agent 根据完成记录生成复盘。

统计数据包括：

```text
完成了哪些节点
哪些节点长期未动
哪些 routine 连续完成/断签
哪些任务被阻塞
摸鱼时长
专注时长
```

输出示例：

```text
今天你完成了 4 个节点，其中 3 个属于 Qt 大作业主线。
「实现 EdgeItem」已经推进，但「自动布局」还没有开始。
你今天有一次 12 分钟的 B 站摸鱼记录，不过总体专注情况不错。
明天建议优先完成「保存/加载图结构」。
```

MVP 可以做“手动点击生成今日复盘”，不一定自动定时。

---

## 7.5 Agent 功能五：对话修改图，作为选做

用户输入：

```text
把“录视频”放到“UI 美化”之后，并且优先级调高。
```

Agent 输出 actions：

```json
{
  "message": "我将为你调整图结构。",
  "actions": [
    {
      "tool": "add_edge",
      "args": {
        "fromTitle": "UI 美化",
        "toTitle": "录视频",
        "edgeType": "dependency"
      }
    },
    {
      "tool": "update_node",
      "args": {
        "title": "录视频",
        "priority": 5
      }
    }
  ]
}
```

程序解析并让用户确认。

这个功能 agent 味很强，但实现复杂度更高，可以作为 bonus。

---

# 8. 第四层：系统增强功能

这些不是主线，但可以增加实用性和展示效果。

---

## 8.1 剪贴板内容变资源节点

### 功能描述

监听剪贴板变化。

当用户复制文本、代码、网址时，桌宠提示：

```text
检测到剪贴板内容，要保存为资源节点吗？
```

用户确认后，创建 Resource 节点，并挂到当前选中节点附近。

### 支持内容

MVP 建议支持：

```text
文本
URL
代码片段
图片
```

第一版可以只做文本和 URL。

### Qt 技术

- `QClipboard`
- `QGuiApplication::clipboard()`
- `QClipboard::dataChanged`

---

## 8.2 文件拖入节点

### 功能描述

用户可以把文件拖到某个节点上，作为附件。

例如：

```text
把 report.docx 拖到“写报告”节点
把参考论文 PDF 拖到“读论文”节点
```

### Qt 技术

- `dragEnterEvent`
- `dropEvent`
- `QMimeData`
- `QFile::copy`

附件保存：

```text
project_dir/attachments/
```

---

## 8.3 摸鱼检测 / 专注模式

### 功能描述

用户对某个节点开启专注模式。

系统检测当前前台窗口，如果发现黑名单应用或网页标题，桌宠提醒。

### 支持设置

```text
当前专注节点
专注时长
允许应用白名单
摸鱼应用黑名单
提醒阈值
```

例如：

```text
白名单：Code.exe, QtCreator.exe, devenv.exe
黑名单：bilibili, steam, youtube
```

### Windows 技术

- `GetForegroundWindow`
- `GetWindowText`
- `GetWindowThreadProcessId`
- `OpenProcess`
- `QueryFullProcessImageName`

### 交互亮点

如果检测到摸鱼，可以创建/更新一个 Reward 或 Distraction 节点：

```text
B 站摸鱼 12 分钟
```

这样摸鱼行为也被纳入图中。

---

# 9. 主界面设计

建议主界面布局：

```text
┌──────────────────────────────────────────────┐
│ 顶部工具栏：新建图 保存 加载 Agent 推荐 专注 │
├───────────────┬──────────────────────────────┤
│ 左侧节点列表   │                              │
│ - 所有节点     │                              │
│ - 今日 due    │        中央任务图区域          │
│ - Routine     │       QGraphicsView           │
│ - Resource    │                              │
├───────────────┤                              │
│ Agent 对话框   │                              │
│ 输入框/按钮    │                              │
├───────────────┴───────────────┬──────────────┤
│ 状态栏：当前节点/专注状态/保存状态             │
└───────────────────────────────┴──────────────┘
```

另一种更简洁布局：

```text
左侧：工具栏 + Agent 面板
中央：任务图
右侧：选中节点属性面板
底部：日志/事件流
```

推荐：

> 中央图区域一定要大，图是主界面，不要让它像附属视图。

---

# 10. 节点 UI 设计

每个节点显示：

```text
┌─────────────────────┐
│ 图标  标题           │
│ 状态 / 优先级        │
│ 预计时间 / streak    │
└─────────────────────┘
```

不同节点类型不同图标：

```text
Task        ✅
Routine     🔁
Resource    📎
Checkpoint  📋
Reward      🎮
```

如果不用 emoji，也可以用简单 icon 或颜色。

节点交互：

- 单击：选中，右侧显示详情
- 双击：编辑
- 右键：菜单
- 拖拽：移动
- Shift + 拖动到另一个节点：创建边
- 点击状态按钮：完成/进行中

---

# 11. 数据存储设计

MVP 推荐使用 JSON 文件。

优点：

- 图结构天然适合 JSON。
- 方便调试。
- 方便让 LLM 生成。
- 不用一开始设计复杂数据库。

后期可以换 SQLite。

---

## 11.1 项目文件结构

```text
PetFlow/
  data/
    default_graph.json
    settings.json
    history.json
  attachments/
    ...
  logs/
    app.log
```

---

## 11.2 graph.json 示例

```json
{
  "version": 1,
  "nodes": [
    {
      "id": "node_001",
      "type": "task",
      "title": "实现图视图",
      "description": "使用 QGraphicsView 展示任务图",
      "status": "doing",
      "priority": 5,
      "estimatedMinutes": 120,
      "actualMinutes": 30,
      "createdAt": "2026-05-01T10:00:00",
      "updatedAt": "2026-05-01T12:00:00",
      "completedAt": null,
      "x": 100,
      "y": 200,
      "tags": ["Qt", "核心"],
      "attachments": []
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "from": "node_001",
      "to": "node_002",
      "type": "dependency",
      "label": ""
    }
  ],
  "pet": {
    "currentNodeId": "node_001",
    "mood": "thinking"
  }
}
```

---

# 12. 推荐代码模块划分

建议项目结构：

```text
src/
  main.cpp

  core/
    Node.h
    Node.cpp
    Edge.h
    Edge.cpp
    GraphModel.h
    GraphModel.cpp
    GraphSerializer.h
    GraphSerializer.cpp
    RecommendationEngine.h
    RecommendationEngine.cpp

  ui/
    MainWindow.h
    MainWindow.cpp
    GraphView.h
    GraphView.cpp
    GraphScene.h
    GraphScene.cpp
    NodeItem.h
    NodeItem.cpp
    EdgeItem.h
    EdgeItem.cpp
    PetItem.h
    PetItem.cpp
    NodeEditorDialog.h
    NodeEditorDialog.cpp
    AgentPanel.h
    AgentPanel.cpp

  agent/
    AgentClient.h
    AgentClient.cpp
    PromptBuilder.h
    PromptBuilder.cpp
    AgentAction.h
    AgentAction.cpp
    AgentActionParser.h
    AgentActionParser.cpp
    AgentActionExecutor.h
    AgentActionExecutor.cpp

  system/
    ClipboardWatcher.h
    ClipboardWatcher.cpp
    FocusMonitor.h
    FocusMonitor.cpp
    AttachmentManager.h
    AttachmentManager.cpp

  util/
    IdGenerator.h
    TimeUtil.h
    JsonUtil.h
```

---

# 13. 核心类设计

## 13.1 Node

```cpp
enum class NodeType {
    Task,
    Routine,
    Resource,
    Checkpoint,
    Reward
};

enum class NodeStatus {
    Todo,
    Doing,
    Done,
    Blocked,
    Paused
};

struct Node {
    QString id;
    NodeType type;
    QString title;
    QString description;
    NodeStatus status;

    int priority = 3;
    int estimatedMinutes = 0;
    int actualMinutes = 0;

    QPointF position;

    QDateTime createdAt;
    QDateTime updatedAt;
    QDateTime completedAt;

    QStringList tags;
    QStringList attachments;

    // routine fields
    QString repeatType; // none/daily/weekly/monthly
    QDateTime lastCompletedAt;
    QDateTime nextDueAt;
    int streak = 0;

    // resource fields
    QString resourceType;
    QString resourcePath;
};
```

---

## 13.2 Edge

```cpp
enum class EdgeType {
    Dependency,
    Routine,
    Recommendation,
    Trigger
};

struct Edge {
    QString id;
    QString from;
    QString to;
    EdgeType type;
    QString label;
};
```

---

## 13.3 GraphModel

负责维护所有节点和边。

```cpp
class GraphModel : public QObject {
    Q_OBJECT

public:
    QString addNode(const Node& node);
    void removeNode(const QString& nodeId);
    void updateNode(const Node& node);

    QString addEdge(const Edge& edge);
    void removeEdge(const QString& edgeId);

    Node* getNode(const QString& nodeId);
    QList<Node> getAllNodes() const;
    QList<Edge> getAllEdges() const;

    QList<Node> predecessors(const QString& nodeId) const;
    QList<Node> successors(const QString& nodeId) const;

    bool wouldCreateDependencyCycle(const QString& from, const QString& to) const;
    bool isBlocked(const QString& nodeId) const;

signals:
    void graphChanged();
    void nodeChanged(QString nodeId);
    void edgeChanged(QString edgeId);
};
```

---

## 13.4 RecommendationEngine

```cpp
class RecommendationEngine {
public:
    explicit RecommendationEngine(GraphModel* model);

    QString recommendNextNode();
    int scoreNode(const Node& node);
    bool isRoutineDue(const Node& node);
    bool isDependencyReady(const Node& node);
    QStringList explainRecommendation(const QString& nodeId);
};
```

---

## 13.5 AgentClient

负责调用 LLM API。

```cpp
class AgentClient : public QObject {
    Q_OBJECT

public:
    explicit AgentClient(QObject* parent = nullptr);

    void generateGraphFromGoal(const QString& goal);
    void splitNode(const Node& node, const QString& context);
    void recommendNext(const QString& graphSummary);
    void reviewToday(const QString& summary);

signals:
    void responseReceived(QString response);
    void errorOccurred(QString error);
};
```

Qt 网络：

```cpp
QNetworkAccessManager
QNetworkRequest
QNetworkReply
```

---

## 13.6 AgentActionExecutor

负责把 Agent 返回的 JSON 操作变成真实图修改。

```cpp
class AgentActionExecutor {
public:
    explicit AgentActionExecutor(GraphModel* model);

    bool executeActions(const QJsonArray& actions);
    bool executeCreateNode(const QJsonObject& args);
    bool executeUpdateNode(const QJsonObject& args);
    bool executeAddEdge(const QJsonObject& args);
    bool executeStartFocusTimer(const QJsonObject& args);
};
```

注意：

> Agent 生成的操作必须先预览，再让用户确认，不能直接执行。

---

# 14. Agent Prompt 设计

## 14.1 从目标生成任务图

```text
你是一个任务规划 Agent。请把用户目标拆解成一张任务图。

要求：
1. 只输出严格 JSON，不要输出 Markdown。
2. 节点数量控制在 6 到 12 个。
3. 节点 type 可选：task, routine, resource, checkpoint, reward。
4. 边 type 可选：dependency, routine, recommendation, trigger。
5. dependency 边表示必须先完成 from 才能做 to。
6. routine 边可以形成环。
7. 每个 task 节点 estimatedMinutes 建议在 15 到 180 之间。
8. priority 为 1 到 5。
9. 输出格式如下：
{
  "nodes": [
    {
      "id": "n1",
      "type": "task",
      "title": "...",
      "description": "...",
      "priority": 3,
      "estimatedMinutes": 60
    }
  ],
  "edges": [
    {
      "from": "n1",
      "to": "n2",
      "type": "dependency"
    }
  ]
}

用户目标：
{{goal}}
```

---

## 14.2 拆分节点

```text
你是一个任务拆分 Agent。请把当前节点拆分成更小的任务节点。

当前节点：
{{node_json}}

相关前置节点：
{{predecessors_json}}

相关后继节点：
{{successors_json}}

要求：
1. 只输出严格 JSON。
2. 子节点数量 3 到 6 个。
3. 每个子节点预计 15 到 60 分钟可完成。
4. 输出 nodes 和 edges。
5. 子节点之间尽量用 dependency 边表达先后关系。
6. 不要重复已有节点。
```

---

## 14.3 下一步推荐解释

```text
你是一个桌宠学习监督 Agent。请根据任务图状态，用简洁友好的中文给出下一步建议。

当前推荐节点：
{{recommended_node}}

推荐理由：
{{reasons}}

当前时间：
{{time}}

用户最近行为：
{{recent_activity}}

要求：
1. 语气像桌宠，可以轻松一点。
2. 不要超过 120 字。
3. 给出一个具体下一步行动。
```

---

## 14.4 每日复盘

```text
你是一个个人工作流复盘 Agent。请根据用户今天的任务图记录，生成简短复盘。

今日完成节点：
{{completed_nodes}}

今日进行中节点：
{{doing_nodes}}

长期未动节点：
{{stale_nodes}}

Routine 情况：
{{routine_summary}}

摸鱼/专注记录：
{{focus_summary}}

要求：
1. 总结今天完成了什么。
2. 指出一个主要问题。
3. 给出明天最推荐的 1-2 个节点。
4. 语气友好但稍微有监督感。
5. 输出中文，控制在 250 字以内。
```

---

# 15. 开发阶段规划

建议分成 5 个阶段。

---

## Phase 1：任务图基础 MVP

目标：做出可以编辑、保存、加载的任务图。

功能：

- 主窗口
- QGraphicsView/QGraphicsScene
- NodeItem 显示
- EdgeItem 显示
- 添加/删除/编辑节点
- 添加/删除边
- 拖动节点
- JSON 保存/加载
- 节点状态切换

验收标准：

```text
可以手动创建一张任务图，并保存后重新打开。
```

---

## Phase 2：节点/边语义和 routine

目标：图不只是画图，而是有任务逻辑。

功能：

- 节点类型：task/routine/resource/checkpoint/reward
- 边类型：dependency/routine/recommendation/trigger
- dependency 成环检测
- blocked 状态判断
- routine 到期判断
- 完成节点后推荐后继节点
- 右侧属性面板

验收标准：

```text
可以创建项目依赖图和 routine 环，并且系统能区分 dependency 环和 routine 环。
```

---

## Phase 3：桌宠图内 Agent

目标：让桌宠参与图交互。

功能：

- PetItem 显示在图中
- 桌宠移动到某节点
- 节点完成后桌宠推荐下一节点
- routine 到期提醒
- 气泡提示
- 简单状态动画/表情

验收标准：

```text
完成一个节点后，桌宠能移动到推荐节点并给出提示。
```

---

## Phase 4：LLM Agent 能力

目标：加入真正的 Agent 规划功能。

功能：

- AgentPanel 对话面板
- 调用 LLM API
- 自然语言生成任务图
- 节点智能拆分
- 本地推荐下一步 + LLM 解释
- 每日复盘
- Agent 返回 JSON 的校验和预览

验收标准：

```text
输入一个目标，Agent 能生成任务图；
右键一个节点，Agent 能拆出子节点。
```

---

## Phase 5：系统增强和打磨

目标：提升展示效果和实用性。

功能可选：

- 剪贴板变资源节点
- 文件拖入节点
- 专注模式
- 摸鱼检测
- 桌面悬浮桌宠
- UI 美化
- 示例图模板
- 自动布局

验收标准：

```text
项目具有完整演示流程和稳定 UI。
```

---

# 16. MVP 功能清单

如果时间有限，最小可交付版本应包含：

## 必做

- 图形化节点编辑
- 图形化边编辑
- 节点类型：task/routine/resource
- 边类型：dependency/routine/recommendation
- 节点状态：todo/doing/done/blocked
- JSON 保存/加载
- dependency 成环检测
- routine 环允许
- 桌宠在图中移动
- 完成节点后推荐下一步
- Agent 生成任务图
- Agent 拆分节点

## 可选

- 摸鱼检测
- 剪贴板资源节点
- 每日复盘
- 桌面悬浮桌宠
- 文件附件
- 自动布局

---

# 17. 推荐分工方式

如果是 2-4 人组队，可以这样分：

## 同学 A：图编辑核心

负责：

- GraphModel
- Node/Edge 数据结构
- QGraphicsView
- NodeItem
- EdgeItem
- 拖拽、连边、右键菜单

## 同学 B：存储和任务逻辑

负责：

- JSON 保存/加载
- 成环检测
- blocked 判断
- routine 到期判断
- 推荐算法
- 节点属性面板

## 同学 C：Agent 模块

负责：

- AgentClient
- PromptBuilder
- LLM API 调用
- JSON 解析
- AgentActionExecutor
- AgentPanel

## 同学 D：桌宠和系统增强

负责：

- PetItem
- 桌宠动画
- 气泡提示
- 剪贴板监听
- 摸鱼检测
- UI 美化

如果只有 2 人：

```text
一人负责图和数据模型
一人负责 Agent、桌宠和增强功能
```

---

# 18. 技术难点和解决方案

## 难点一：QGraphicsView 连边交互复杂

建议简化：

第一版不要做“拖线连边”，可以做：

```text
选中节点 A
右键节点 B
选择“从 A 连到 B”
弹窗选择边类型
```

后续再做拖线连接。

---

## 难点二：图自动布局复杂

建议：

MVP 不做复杂自动布局。

可以先支持：

- 用户手动拖动
- Agent 生成节点时按网格排布
- 简单分层布局

简单布局：

```cpp
x = layer * 220;
y = indexInLayer * 120;
```

如果不会分层，就直接环形/网格排布。

---

## 难点三：LLM 输出 JSON 不稳定

解决方案：

1. Prompt 强调“只输出 JSON”。
2. 程序提取第一个 `{` 到最后一个 `}`。
3. 用 `QJsonDocument::fromJson` 解析。
4. 解析失败则显示原文，并提示用户重试。
5. 所有 Agent 操作都需要用户确认。

---

## 难点四：有环图和依赖逻辑冲突

解决方案：

把边类型区分清楚。

```text
dependency 参与阻塞判断和成环检测
routine/recommendation 不参与 dependency 成环检测
```

---

## 难点五：桌宠动画成本高

解决方案：

- 初期用静态 PNG。
- 不同状态换不同图片。
- 移动用 `QPropertyAnimation` 或定时器插值。
- 后期再加 GIF。

---

# 19. 演示脚本建议

最终展示可以这样安排：

1. 打开 PetFlow，中央是一张空白任务图，桌宠在旁边待机。
2. 用户输入：

   ```text
   帮我规划一个两周内完成 Qt 桌宠任务图项目的计划。
   ```

3. Agent 自动生成任务图。
4. 系统展示生成节点和边，用户点击确认导入。
5. 桌宠移动到第一个推荐节点：

   ```text
   先从「需求分析」开始吧！
   ```

6. 用户完成“需求分析”。
7. 桌宠沿 dependency 边移动到“设计数据结构”。
8. 用户右键“实现图视图”，选择“Agent 拆分节点”。
9. Agent 自动生成子图。
10. 用户创建一个 routine 环：

   ```text
   写代码 -> 测试 -> 记录 bug -> 修复 -> 写代码
   ```

11. 展示 dependency 边成环会被禁止，而 routine 边可以成环。
12. 打开剪贴板/摸鱼检测/复盘等 bonus 功能。
13. 最后 Agent 生成今日复盘。

这个演示能够清楚体现：

```text
图结构
有环 routine
桌宠交互
Agent 规划
Qt 图形界面能力
```

---

# 20. 最终建议实现优先级

按性价比排序：

```text
1. 图编辑和保存加载
2. 节点/边类型
3. routine 环和 dependency 成环检测
4. 桌宠在图中移动和提示
5. Agent 生成任务图
6. Agent 拆分节点
7. 推荐下一步
8. 每日复盘
9. 剪贴板资源节点
10. 摸鱼检测
11. 桌面悬浮桌宠
12. 文件附件和自动布局
```

---

# 21. 可以写进报告的项目描述

> PetFlow 是一个基于任务图的桌宠 Agent 工作流管理器。本项目没有采用传统日历或列表式 todo，而是将用户的任务、routine、资源、奖励和检查点统一建模为一张带类型的有向图。依赖边表达任务前后关系，循环边表达 routine，推荐边表达可选路径，触发边表达自动提醒。桌宠作为图上的 Agent，根据图结构、节点状态、周期规则和用户行为进行任务推荐、routine 提醒、节点拆分和进度复盘。项目结合了 Qt 图形视图框架、图算法、JSON 持久化、LLM API 调用和桌宠交互，适合表达复杂项目规划和非线性个人工作流。

---

# 22. 最终版本目标

理想最终效果：

> 用户打开软件后看到的不是日历，而是一张自己的任务地图。  
> 用户可以手动编辑这张地图，也可以让 Agent 从自然语言目标生成地图。  
> 桌宠会在地图中移动，提醒用户当前该推进哪个节点。  
> 对于 routine，图中可以自然形成环。  
> 对于复杂任务，Agent 可以把节点拆成子图。  
> 对于用户行为，系统可以进行轻量监督和复盘。  

这会是一个比普通 Qt todo-list 更有辨识度、更适合演示，也更有技术含量的大作业。
