# PetFlow 动态日历功能设计

## 1. 背景与目的

在学习和项目开发中，传统日历和待办清单通常只能表达“什么时候做什么”，很难表达任务之间的依赖、循环、资源引用和阶段性检查关系。面对课程大作业、长期习惯、复习计划或软件开发流程时，用户更需要一种能够呈现工作流结构的工具。

**PetFlow 是一个基于 Python 实现的桌宠式任务图工作流管理器。** 它用“任务图”代替传统日历和 todo-list：节点表示任务、习惯、资源、检查点或奖励，边表示依赖、循环、推荐或触发关系。桌宠 Agent 会根据任务图状态、时间和用户行为，提醒用户下一步行动、辅助拆分任务，并生成阶段性复盘。

本项目选择 Python 作为主要开发语言。原因是 Python 更适合快速完成 GUI、JSON 数据存储、LLM API 调用和系统能力集成，能降低三人合作时的工程复杂度，同时满足大作业对 Python 面向对象 GUI 项目的要求。

## 2. 技术选型

### 2.1 推荐技术栈

- **开发语言**：Python 3.10+
- **GUI 框架**：Tkinter
- **图形绘制**：Tkinter Canvas
- **数据存储**：JSON 文件
- **HTTP 请求**：requests 或 httpx
- **系统剪贴板**：Tkinter clipboard API，必要时使用 pyperclip
- **Windows 前台窗口检测**：pywin32，作为选做功能
- **项目结构**：面向对象分层设计

### 2.2 为什么不用 Qt 作为默认方案

原始设想中使用 Qt 的 `QGraphicsView` 和 `QGraphicsScene` 实现图编辑，这在专业桌面软件中很合适。但对于课程大作业，Qt 方案会带来额外的环境配置和学习成本，尤其是多人协作时容易卡在 Qt 版本、安装包、打包和界面类设计上。

Python + Tkinter 更适合作为本项目的默认实现路线：

- Tkinter 是 Python 标准库，环境配置简单。
- Canvas 足以完成节点、边、拖拽、缩放、右键菜单和桌宠动画。
- JSON、网络请求、LLM API 调用在 Python 中实现更直接。
- 三个组员可以更容易按模块分工。

如果后期时间充足，也可以将 GUI 框架替换为 PySide6/PyQt6，但 MVP 阶段建议先用 Tkinter 做出完整功能闭环。

## 3. 项目核心亮点

### 3.1 任务图：重构工作流的底层逻辑

PetFlow 放弃传统线性清单，把任务、习惯、资源与奖励组织成一张有向图。用户不仅能看到“有哪些任务”，还能看到“哪些任务依赖哪些任务”“哪些流程会循环”“完成一个节点后应该触发什么”。

### 3.2 桌宠 Agent：有交互感的任务向导

桌宠不是单纯装饰，而是任务图上的可视化 Agent。它会停留在当前推荐节点旁边，在用户完成节点后移动到下一步任务附近，并通过气泡提示 routine 到期、任务阻塞或摸鱼行为。

### 3.3 轻量 AI 系统：从目标到复盘

系统通过 LLM API 提供三类能力：根据自然语言目标生成初始任务图，对复杂节点进行智能拆分，以及根据当天完成记录生成复盘文本。为了保证项目可控，推荐结果先以 JSON 预览形式展示，由用户确认后再写入图数据。

### 3.4 系统增强：连接真实学习场景

项目可以监听剪贴板，把复制的链接、文本或代码片段快速保存为资源节点；也可以在选做阶段检测前台窗口，实现专注模式和摸鱼提醒。

## 4. 用户使用场景

### 场景一：规划课程大作业

用户输入：

```text
我想两周内完成一个 Python 桌宠任务图项目，需要图编辑、桌宠、Agent 拆任务、演示视频和报告。
```

Agent 自动生成任务图：

```text
确定需求 -> 设计数据结构 -> 实现图编辑
                         -> 实现桌宠
                         -> 实现 Agent
实现图编辑 + 实现桌宠 + 实现 Agent -> UI 美化 -> 录制演示视频 -> 写报告
```

用户确认后，系统将这些节点和边加入 Canvas 图编辑区。

### 场景二：Routine 环

用户创建循环工作流：

```text
写代码 -> 测试 -> 记录 bug -> 修复 bug -> 写代码
```

这类边被标记为 Routine 边，允许形成环。每完成一个节点后，桌宠移动到下一个节点旁，并提示：

```text
下一步该测试啦，要不要开始 25 分钟专注？
```

### 场景三：节点智能拆分

用户右键点击“实现图编辑界面”，选择“Agent 拆分”。Agent 返回：

```text
设计 Canvas 坐标系统
绘制任务节点
绘制有向边
实现节点拖拽
实现右键菜单
保存节点坐标
```

程序先展示拆分预览，用户确认后再生成子节点和依赖边。

### 场景四：专注模式提醒

用户把当前节点设为“写报告”，开启专注模式。如果系统检测到用户长时间停留在娱乐网站或无关窗口，桌宠弹出提示：

```text
你当前的任务是「写报告」。刚才离开了一段时间，要记录为休息节点，还是回到任务？
```

该功能作为选做，不影响核心 MVP。

## 5. 详细功能设计

PetFlow 分为四层功能：

```text
第一层：任务图核心
第二层：桌宠交互
第三层：Agent 能力
第四层：系统增强能力
```

### 5.1 任务图核心

任务图是项目基础，由数据模型和 Canvas 视图共同实现。

#### 节点类型

- **Task 任务节点**：一次性任务，包含标题、描述、优先级、预计耗时、实际耗时和状态。
- **Routine 循环节点**：周期性任务或习惯，包含重复周期、下次到期时间和连续完成天数。
- **Resource 资源节点**：存放 URL、本地文件、文本、代码片段等资料，不一定需要完成。
- **Checkpoint 检查点节点**：阶段性里程碑，包含 checklist。
- **Reward 奖励节点**：表示休息或奖励，例如“刷视频 15 分钟”。

#### 节点状态

具备执行属性的节点支持五种状态：

```text
todo       未开始
doing      进行中
done       已完成
blocked    被阻塞
paused     暂停
```

界面上用不同颜色区分节点状态。例如 todo 用浅蓝，doing 用黄色，done 用绿色，blocked 用红色，paused 用紫色。

#### 边类型

- **Dependency 依赖边**：表示前置依赖，禁止形成环。
- **Routine 循环边**：表示周期性流程，允许形成环。
- **Recommendation 推荐边**：表示建议路径，允许形成环。
- **Trigger 触发边**：表示完成源节点后提醒目标节点。

#### 图编辑操作

Canvas 主界面需要支持：

- 新建节点
- 编辑节点
- 删除节点
- 拖拽节点
- 创建边
- 删除边
- 修改节点状态
- 修改边类型
- 保存和加载 JSON
- 简单缩放和平移
- 右键菜单

MVP 阶段可以先实现“点击按钮进入连边模式”，即先点击源节点，再点击目标节点创建边，降低交互复杂度。

### 5.2 桌宠交互

桌宠在 Tkinter Canvas 中实现为一个可移动的图形对象，可以先使用圆形、图片或 GIF 帧动画表示。

#### 图内桌宠

主窗口打开时，桌宠显示在任务图中：

- 当前无任务时停在画布角落。
- 用户选择一个进行中节点后，桌宠移动到该节点旁。
- 用户完成节点后，系统根据边和推荐算法计算下一步，桌宠移动到推荐节点旁。
- Routine 到期时，桌宠移动到对应节点旁并显示气泡。

#### 桌宠动作

MVP 阶段只需实现简单动作：

```text
idle     待机
move     移动
happy    完成任务
angry    摸鱼提醒
think    Agent 思考
sleep    长时间无操作
```

动画可以用 Canvas 定时器 `after()` 实现，例如每 30 毫秒更新一次桌宠坐标。

#### 桌面悬浮形态

悬浮桌宠作为选做功能。可以用单独的 `Toplevel` 窗口实现无边框小窗，显示当前任务、倒计时和简单提醒。若时间不足，可只实现图内桌宠。

### 5.3 Agent 能力

Agent 模块由本地规则引擎和 LLM 客户端组成。

#### 自然语言生成任务图

用户输入目标后，程序构造 Prompt，要求 LLM 返回固定 JSON：

```json
{
  "nodes": [
    {"id": "n1", "type": "task", "title": "确定需求", "priority": 4},
    {"id": "n2", "type": "task", "title": "设计数据结构", "priority": 5}
  ],
  "edges": [
    {"source": "n1", "target": "n2", "type": "dependency"}
  ]
}
```

程序对 JSON 做校验，确认节点字段、边字段和依赖成环规则后，弹出预览窗口。用户确认后再导入主图。

#### 节点智能拆分

用户右键点击节点，选择“Agent 拆分”。程序将当前节点标题、描述、前置节点和后置节点传给 LLM，要求返回 3 到 6 个可执行子任务。返回内容同样先预览，再写入模型。

#### 下一步行动推荐

推荐模块优先使用本地评分算法，避免所有推荐都依赖网络。评分因素包括：

- 前置依赖是否已完成
- 节点优先级
- 节点是否正在进行
- Routine 是否到期
- 预计耗时是否适合当前时间
- 是否长期 blocked

LLM 只负责把本地推荐结果解释成一句自然语言提示。

#### 每日/每周复盘

程序根据历史记录统计：

- 完成了哪些节点
- 哪些节点长期未推进
- Routine 是否断签
- 专注时间和休息时间
- 明天建议优先处理什么

如果 API 可用，LLM 生成自然语言复盘；如果 API 不可用，程序使用本地模板生成基础复盘。

### 5.4 系统增强能力

#### 剪贴板内容变资源节点

使用 Tkinter 剪贴板 API 定时检查剪贴板内容。若检测到 URL、文件路径或较长文本，弹窗询问是否保存为 Resource 节点。用户确认后，资源节点自动出现在当前激活节点附近。

#### 文件附件拖入

Tkinter 原生拖拽能力较弱，MVP 阶段可以先用“添加附件”按钮选择文件。若需要拖拽，可引入 `tkinterdnd2` 作为选做依赖。

#### 专注模式与摸鱼检测

Windows 下可以使用 pywin32 获取当前前台窗口标题和进程名。用户对某个节点开启专注模式后，系统每隔数秒检测当前窗口：

- 白名单：IDE、浏览器文档页、PDF 阅读器等。
- 黑名单：视频网站、游戏、社交娱乐应用等。

检测到黑名单时，桌宠显示提醒，并可将这段时间记录为 Reward 或 Distraction 节点。该功能作为展示亮点即可，不建议放在 MVP 的关键路径上。

## 6. 底层数据存储

### 6.1 JSON 文件结构

为了兼容 LLM 输出并降低开发复杂度，系统使用 JSON 作为项目文件格式。

```json
{
  "version": 1,
  "nodes": [
    {
      "id": "node_001",
      "type": "task",
      "title": "实现 Canvas 图编辑",
      "description": "绘制节点、边并支持拖拽",
      "status": "todo",
      "priority": 4,
      "estimated_minutes": 120,
      "actual_minutes": 0,
      "created_at": "2026-05-03T10:00:00",
      "updated_at": "2026-05-03T10:00:00",
      "completed_at": null,
      "x": 120,
      "y": 180,
      "tags": ["GUI", "MVP"],
      "attachments": []
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "source": "node_001",
      "target": "node_002",
      "type": "dependency"
    }
  ],
  "pet": {
    "current_node_id": "node_001",
    "state": "idle",
    "x": 80,
    "y": 120
  },
  "history": []
}
```

### 6.2 数据类设计

推荐使用 `dataclasses` 定义核心数据类：

```python
from dataclasses import dataclass, field

@dataclass
class Node:
    id: str
    type: str
    title: str
    description: str = ""
    status: str = "todo"
    priority: int = 3
    estimated_minutes: int = 30
    actual_minutes: int = 0
    x: float = 100
    y: float = 100
    tags: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)

@dataclass
class Edge:
    id: str
    source: str
    target: str
    type: str = "dependency"
```

## 7. 模块架构

推荐目录结构：

```text
petflow/
  main.py
  models/
    node.py
    edge.py
    graph_model.py
  ui/
    main_window.py
    graph_canvas.py
    dialogs.py
    pet_view.py
  services/
    storage_service.py
    recommendation_engine.py
    agent_client.py
    agent_executor.py
    clipboard_watcher.py
    focus_monitor.py
  assets/
    pet_idle.png
    pet_happy.png
  data/
    sample_graph.json
```

### 7.1 Core 模块

- `Node`：节点数据类。
- `Edge`：边数据类。
- `GraphModel`：维护节点和边，负责增删改查、依赖成环检测、状态更新。
- `RecommendationEngine`：根据图状态推荐下一步节点。

### 7.2 UI 模块

- `MainWindow`：主窗口，负责菜单栏、工具栏和整体布局。
- `GraphCanvas`：基于 Tkinter Canvas 的图编辑区域，负责绘制节点、边、桌宠和气泡。
- `NodeDialog`：节点编辑窗口。
- `EdgeDialog`：边类型编辑窗口。
- `AgentDialog`：自然语言输入、Agent 结果预览和确认。

### 7.3 Agent 模块

- `AgentClient`：封装 LLM API 请求。
- `AgentExecutor`：校验 LLM 返回 JSON，并把确认后的动作写入 `GraphModel`。
- `PromptBuilder`：集中管理生成任务图、拆分节点、复盘等 Prompt。

### 7.4 System 模块

- `StorageService`：保存和加载 JSON。
- `ClipboardWatcher`：监听剪贴板变化。
- `FocusMonitor`：检测前台窗口，选做。

## 8. 关键类职责

### 8.1 GraphModel

`GraphModel` 是整个项目的核心数据层，负责：

- 添加、删除、编辑节点
- 添加、删除、编辑边
- 保存节点坐标
- 查询前置和后置节点
- 判断 Dependency 边是否形成环
- 记录节点状态变化历史
- 提供可序列化的 JSON 数据

### 8.2 GraphCanvas

`GraphCanvas` 负责把 `GraphModel` 渲染成可交互界面：

- 根据节点坐标绘制矩形或圆角矩形
- 根据边类型绘制不同颜色和线型
- 支持节点拖拽
- 支持右键菜单
- 支持连边模式
- 将用户操作同步回 `GraphModel`

### 8.3 RecommendationEngine

推荐算法优先本地实现。伪代码：

```text
遍历所有未完成节点
  如果 dependency 前置节点未完成，跳过
  score = priority * 10
  如果节点状态是 doing，score += 20
  如果 routine 到期，score += 30
  如果预计耗时较短，score += 5
选择 score 最高的节点
```

### 8.4 AgentClient

`AgentClient` 只负责网络请求，不直接修改图数据。所有 LLM 输出必须经过 JSON 解析和字段校验，防止格式错误破坏项目文件。

## 9. 开发阶段规划

### Phase 1：任务图 MVP

目标是做出可演示的基础图编辑器：

- 搭建 Tkinter 主窗口
- 使用 Canvas 绘制节点和边
- 支持新增、编辑、删除节点
- 支持拖拽节点
- 支持创建 dependency 边
- 支持保存和加载 JSON

### Phase 2：语义图逻辑

目标是让任务图有真实业务含义：

- 实现五种节点类型
- 实现四种边类型
- 实现节点状态切换
- 实现 Dependency 成环检测
- 实现 Routine 环
- 实现本地下一步推荐

### Phase 3：桌宠交互

目标是形成项目特色：

- 在 Canvas 上绘制桌宠
- 实现桌宠移动动画
- 完成节点后移动到推荐节点
- Routine 到期时显示气泡提醒
- 长时间无操作时进入 sleep 状态

### Phase 4：Agent 能力

目标是实现 AI 亮点：

- 实现 Agent 输入窗口
- 调用 LLM API
- 自然语言生成任务图
- 节点智能拆分
- JSON 结果预览和确认
- 每日/每周复盘

### Phase 5：系统增强与打磨

目标是完善演示效果：

- 剪贴板内容转资源节点
- 文件附件选择
- 专注模式和前台窗口检测
- UI 配色和图标优化
- 准备演示数据和演示脚本

## 10. 三人分工建议

### 组员 A：数据模型与图逻辑

- `Node`、`Edge`、`GraphModel`
- JSON 保存和加载
- Dependency 成环检测
- 节点状态和历史记录

### 组员 B：GUI 与图编辑

- Tkinter 主窗口
- Canvas 节点和边绘制
- 节点拖拽
- 右键菜单
- 节点和边编辑对话框

### 组员 C：Agent、桌宠和系统增强

- 桌宠绘制和动画
- 下一步推荐提示
- AgentClient 和 Prompt
- LLM 结果预览
- 剪贴板监听
- 专注模式选做功能

## 11. MVP 功能清单

必须完成：

- Python 面向对象项目结构
- Tkinter GUI 主窗口
- Canvas 可视化任务图
- 节点创建、编辑、删除、拖拽
- 边创建和删除
- JSON 保存和加载
- 至少三种节点类型：Task、Routine、Resource
- 至少两种边类型：Dependency、Routine
- Dependency 成环检测
- 简单桌宠和气泡提示
- 本地下一步推荐

建议完成：

- Agent 生成任务图
- Agent 拆分节点
- 每日复盘
- 剪贴板内容转资源节点

选做：

- 桌面悬浮桌宠
- 前台窗口检测
- 拖拽文件到节点
- 更丰富的动画和主题皮肤

## 12. 技术难点与解决方案

### 难点一：Canvas 连边交互容易混乱

解决方案：使用“连边模式”。用户点击“创建边”按钮后，先选择源节点，再选择目标节点，最后弹出边类型选择窗口。

### 难点二：图布局复杂

解决方案：MVP 不做复杂自动布局，只保存用户拖拽后的坐标。Agent 生成节点时使用简单的分层布局，把节点按依赖层级横向或纵向排列。

### 难点三：LLM 返回 JSON 不稳定

解决方案：要求 LLM 只返回 JSON；程序使用 `json.loads()` 解析；解析失败时展示原始文本并提示重试；写入图之前必须经过字段校验和用户确认。

### 难点四：依赖边不能成环，但 Routine 边允许成环

解决方案：成环检测只在新增 Dependency 边时执行。Routine、Recommendation 和 Trigger 边不参与依赖成环判断。

### 难点五：桌宠动画成本高

解决方案：MVP 用 Canvas 图形或少量 PNG 图片实现，不追求复杂骨骼动画。核心是“桌宠会响应任务状态”，而不是动画本身多精细。

## 13. 演示脚本建议

演示时可以按以下流程：

1. 打开 PetFlow，展示空白任务图。
2. 手动创建几个任务节点和依赖边。
3. 拖动节点，展示图编辑能力。
4. 保存项目，再重新加载。
5. 创建 Routine 环，说明普通 todo-list 难以表达循环流程。
6. 标记一个节点为 done，桌宠移动到推荐节点旁。
7. 打开 Agent 窗口，输入课程大作业目标，生成任务图预览。
8. 对一个复杂节点执行智能拆分。
9. 复制一个链接，展示剪贴板转资源节点。
10. 展示每日复盘或专注提醒。

## 14. 最终版本目标

最终版本不追求替代成熟日历软件，而是突出课程设计中的综合能力：

- 使用 Python 面向对象方法组织项目。
- 使用 Tkinter 实现多个窗口和对话框。
- 使用 Canvas 实现可交互的任务图。
- 使用 JSON 完成持久化。
- 使用本地算法处理图逻辑和推荐。
- 使用 LLM API 展示智能化能力。
- 使用桌宠交互形成差异化亮点。

一句话描述：

> PetFlow 是一个基于 Python 和 Tkinter 的桌宠式任务图工作流管理器，它把任务、习惯、资源和奖励组织成可交互的有向图，并通过桌宠 Agent 提供推荐、提醒、拆分和复盘能力。
