# PetFlow 开发路线图

本文档描述从当前基础框架到最终演示版本的开发路径。目标是让三名组员可以按阶段并行推进，同时保证每一步都有清晰的验收标准。

当前基础框架已经完成：

- Python 3.12 + Conda 环境。
- `domain / app / repositories / services / ui / agent / system` 分层。
- JSON 仓储、图模型、枚举、Dependency 成环检测。
- Tkinter 主窗口和 Canvas 占位。
- 基础单元测试。

后续开发必须遵守 `docs/architecture.md` 和 `docs/development.md` 中的模块边界。

## 1. 总体开发策略

开发顺序遵循一条主线：

```text
任务图可编辑 -> 图数据可保存 -> 图语义可运行 -> 桌宠可响应 -> Agent 可辅助 -> 系统增强和演示打磨
```

不要先做炫酷动画或 LLM 接入。任务图编辑和数据持久化是所有高级功能的基础，必须优先稳定。

## 2. 里程碑总览

```text
M0 基础框架                 已完成
M1 图编辑主链路             节点绘制、拖拽、创建、编辑、删除
M2 边编辑与持久化闭环        连边、删边、保存、加载、样例数据
M3 语义图与推荐              基础状态流转、依赖推荐、Routine 到期权重已完成
M4 桌宠图内交互              图内桌宠绘制、气泡、完成任务响应已完成
M5 Agent 能力                生成任务图、拆分节点、结果预览、复盘
M6 系统增强与最终打磨        剪贴板、附件、专注模式、UI 美化、演示脚本
```

建议至少完成 M1 到 M4。M5 是项目亮点，建议完成核心两项：生成任务图和拆分节点。M6 作为加分项和演示增强。

## 3. M1：图编辑主链路

### 目标

让用户能在 Canvas 上看到真实节点，并完成基础节点操作。

### 主要任务

#### 组员 A：领域和服务补齐

- 在 `GraphService` 中补齐节点更新方法：
  - `update_node(...)`
  - `rename_node(...)`
  - `update_node_detail(...)`
- 为 `Node` 字段校验补充基础规则：
  - title 不能为空
  - priority 限制在 1 到 5
  - estimated_minutes 不能为负数
- 增加对应单元测试。

#### 组员 B：Canvas 节点绘制

- 在 `GraphCanvas` 中实现节点绘制。
- 根据 `NodeStatus` 和 `NodeType` 给节点设置颜色。
- 建立 Canvas item id 到 node id 的映射。
- 支持单击选中节点。
- 支持拖拽节点，并通过 `GraphService.move_node()` 更新模型。
- 支持双击节点打开编辑对话框。

#### 组员 C：Dialog 基础组件

- 新建 `src/petflow/ui/dialogs.py`。
- 实现 `NodeDialog`：
  - title
  - description
  - node type
  - status
  - priority
  - estimated minutes
- Dialog 只负责收集输入，不直接修改 `GraphModel`。

### 验收标准

- 点击“New Node”可以创建节点。
- 节点显示在 Canvas 上。
- 节点可以拖动，坐标会更新。
- 双击节点可以编辑标题和描述。
- 删除节点后 Canvas 会刷新。
- 单元测试通过。

### 推荐提交

```text
feat: add node editing workflow
```

## 4. M2：边编辑与持久化闭环

### 目标

完成任务图最小闭环：节点和边都能创建、编辑、保存、加载。

### 主要任务

#### 组员 A：图规则和仓储

- 完善 `GraphModel.add_edge()` 和 `update_edge()` 的测试。
- 增加保存加载测试：
  - 保存一个含节点和边的图。
  - 重新加载后字段一致。
- 在 `data/` 下提供一个演示样例文件，例如 `sample_graph.json`。

#### 组员 B：Canvas 边绘制和连边模式

- 实现边绘制：
  - Dependency：实线箭头
  - Routine：绿色或虚线箭头
  - Recommendation：浅色虚线
  - Trigger：强调色箭头
- 实现连边模式：
  - 点击工具栏“Create Edge”
  - 选择源节点
  - 选择目标节点
  - 弹出边类型选择
  - 调用 `GraphService.create_edge()`
- 支持选中边和删除边。

#### 组员 C：文件操作 UI

- 工具栏增加：
  - Save
  - Load
  - Save As，选做
  - Open Sample，选做
- 保存失败或加载失败要弹窗提示。

### 验收标准

- 能创建 A -> B 的 Dependency 边。
- 试图创建 B -> A 的 Dependency 边时被拒绝并提示。
- 能创建 Routine 环。
- 保存后重新打开，节点坐标和边关系保持一致。
- `data/sample_graph.json` 可用于演示。

### 推荐提交

```text
feat: complete graph persistence workflow
```

## 5. M3：语义图与推荐

当前进展：

- `RecommendationEngine` 已支持 Dependency 前置检查、done/blocked 跳过、doing 加权、priority 加权、Routine 到期加权。
- `GraphService.update_node_status()` 已记录状态变化历史，标记 done 时写入 `completed_at`。
- Routine 节点标记 done 时会更新 `last_completed_at`、`next_due_at` 和 `streak`，当前支持 daily、weekly、monthly 的基础日期计算。
- UI 已支持节点右键状态切换、工具栏 `Mark Done` 和 `Recommend Next`。
- 已增加推荐算法和状态流转单元测试。

### 目标

让任务图不仅能画，还能表达真实工作流。

### 主要任务

#### 组员 A：状态和推荐算法

- 完善 `RecommendationEngine`：
  - 前置 Dependency 未完成的节点不能推荐。
  - doing 节点加权。
  - priority 高的节点加权。
  - Routine 到期节点加权。
  - blocked 节点降低权重或跳过。
- 增加推荐算法测试。
- 记录节点状态变化历史。

#### 组员 B：状态切换 UI

- 节点右键菜单：
  - Mark Todo
  - Mark Doing
  - Mark Done
  - Mark Blocked
  - Mark Paused
  - Delete Node
- 状态变化后节点颜色实时刷新。
- 工具栏或侧边栏显示当前推荐节点。

#### 组员 C：Routine 基础逻辑

- 为 Routine 节点补充字段编辑：
  - repeat_type
  - next_due_at
  - streak
- MVP 可以先只支持 daily 和 weekly。
- 完成 Routine 后刷新 next_due_at，选做。

### 验收标准

- Dependency 前置未完成时，后置节点不能被推荐。
- 节点状态切换后颜色正确。
- 点击“Recommend Next”能得到一个合理节点。
- Routine 节点有独立样式和基础字段。

### 推荐提交

```text
feat: add semantic graph states and recommendation
```

## 6. M4：桌宠图内交互

当前进展：

- 新增 `PetService`，监听节点状态变化事件。
- 节点标记 done 后，桌宠会移动到推荐节点旁，并显示下一步提示。
- `Recommend Next` 会让桌宠进入 think 状态并移动到推荐节点旁。
- 新增 `PetView`，用 Canvas 图形绘制桌宠和气泡。
- `PetState` 已随项目 JSON 保存和加载。

### 目标

让桌宠成为项目特色，而不是静态装饰。

### 主要任务

#### 组员 A：事件和推荐衔接

- 在节点完成时发布事件。
- 让桌宠模块能监听节点状态变化。
- 完成节点后触发推荐下一步。

#### 组员 B：Canvas 桌宠渲染

- 新建 `src/petflow/ui/pet_view.py`。
- 桌宠可以先用 Canvas 圆形、简单图片或少量 PNG。
- 实现桌宠位置更新。
- 桌宠位置保存到 `PetState`。

#### 组员 C：桌宠动作和气泡

- 实现简单动作状态：
  - idle
  - move
  - happy
  - think
  - sleep
- 实现气泡提示。
- 完成节点后，桌宠移动到推荐节点旁并显示一句提示。

### 验收标准

- 主界面能看到桌宠。
- 用户完成节点后，桌宠移动到推荐节点旁。
- Routine 到期或推荐节点出现时，桌宠能显示气泡。
- 即使没有图片资源，桌宠也能用 Canvas 图形正常演示。

### 推荐提交

```text
feat: add in-graph pet assistant
```

## 7. M5：Agent 能力

### 目标

完成项目智能化亮点：自然语言生成任务图和节点拆分。

### 主要任务

#### 组员 A：Agent 输出校验

- 新建 proposal 校验逻辑：
  - nodes 必须是列表
  - edges 必须是列表
  - 节点必须有 title
  - 边必须有 source 和 target
  - type 必须属于枚举
- LLM 输出解析失败时不能影响当前图。
- 增加测试。

#### 组员 B：AgentDialog

- 实现 Agent 输入窗口。
- 支持两个模式：
  - Generate Graph
  - Split Node
- 显示 JSON 预览或结构化预览。
- 用户确认后才调用 `AgentExecutor`。

#### 组员 C：AgentClient 和 Prompt

- 完善 `PromptBuilder`：
  - 生成任务图 Prompt
  - 拆分节点 Prompt
  - 复盘 Prompt
- 实现 `AgentClient`。
- API Key 通过环境变量读取，不写入代码。
- 如果没有 API Key，提供 mock 模式，返回固定样例，保证演示不依赖网络。

### 验收标准

- 输入一段目标，能生成任务图预览。
- 用户确认后，节点和边加入 Canvas。
- 右键节点执行“Agent Split”，能生成子任务预览。
- API 不可用时，mock 模式仍可演示。

### 推荐提交

```text
feat: add agent graph proposal workflow
```

## 8. M6：系统增强与最终打磨

### 目标

完善演示体验，形成有辨识度的大作业成品。

### 主要任务

#### 剪贴板资源节点

- `ClipboardWatcher` 定时检查剪贴板内容。
- 检测 URL 或长文本。
- 弹窗询问是否保存为 Resource 节点。
- Resource 节点出现在当前节点附近。

#### 文件附件

- MVP 用文件选择框，不强求拖拽。
- 文件路径写入 `attachments`。
- 节点详情中显示附件列表。

#### 专注模式

- 先实现 UI 开关和计时。
- Windows 下 `FocusMonitor` 用 pywin32 获取前台窗口，作为选做。
- macOS 或其他平台可以只展示模拟检测，不影响主流程。

#### UI 打磨

- 统一配色。
- 增加状态栏：
  - 当前节点
  - 推荐节点
  - 保存状态
  - 专注模式状态
- 准备演示样例图。

### 验收标准

- 复制链接后能快速变成 Resource 节点。
- 节点能添加附件路径。
- 有可展示的专注模式入口。
- 项目启动后默认能加载演示图或快速创建演示图。

### 推荐提交

```text
feat: add system enhancements and demo polish
```

## 9. 最终验收清单

最终提交前必须逐项检查：

- 环境能创建：`conda env create -f environment.yml`
- 程序能启动：`PYTHONPATH=src python -m petflow.main`
- 单元测试通过。
- 能创建、编辑、删除节点。
- 能拖拽节点。
- 能创建、删除边。
- Dependency 成环会被拒绝。
- Routine 环允许创建。
- JSON 保存和加载正确。
- 至少三种节点类型可见：Task、Routine、Resource。
- 至少两种边类型可见：Dependency、Routine。
- 能切换节点状态。
- 能推荐下一步。
- 桌宠能响应节点完成。
- Agent 生成任务图或 mock 生成任务图可演示。
- 节点拆分可演示。
- 有演示样例数据。
- 文档和报告中的技术路线一致。

## 10. 推荐演示路线

演示不要从空讲概念开始，直接操作软件：

1. 打开 PetFlow，展示示例任务图。
2. 新建一个任务节点。
3. 拖动节点，展示 Canvas 交互。
4. 创建 Dependency 边。
5. 尝试创建 Dependency 环，展示系统拒绝。
6. 创建 Routine 环，展示系统允许。
7. 标记一个节点为 done，展示推荐节点变化。
8. 桌宠移动到推荐节点旁并显示气泡。
9. 打开 Agent 窗口，输入课程大作业目标。
10. 展示 Agent 生成任务图预览。
11. 对一个复杂节点执行拆分。
12. 保存、关闭、重新加载，展示持久化。
13. 展示剪贴板资源节点或专注模式作为加分项。

## 11. 风险控制

### 风险一：Canvas 交互耗时过长

优先实现按钮式连边和右键菜单，不追求复杂手势。缩放和平移可以后置。

### 风险二：Agent API 不稳定

必须保留 mock 模式。演示时如果网络或 API Key 不可用，仍然能展示 Agent 流程。

### 风险三：桌宠动画成本高

桌宠核心价值是“响应任务图状态”，不是复杂动画。可以用 Canvas 图形先完成交互，再替换图片。

### 风险四：系统检测跨平台复杂

专注模式先做 UI 和计时，前台窗口检测作为 Windows 加分项，不放在主线。

### 风险五：多人修改冲突

严格按模块分工。涉及公共领域模型的改动，先同步字段和 JSON 结构，再分别开发 UI 或 Agent。

## 12. 建议时间分配

如果总开发时间较紧，可以按比例分配：

```text
30%  图编辑和持久化
20%  语义规则和推荐
15%  桌宠交互
20%  Agent 能力
15%  系统增强、UI 打磨、报告和演示
```

如果时间不足，优先砍选做功能，不能砍任务图编辑、保存加载、依赖规则和桌宠响应。
