# PetFlow 架构设计规范

本文档用于约束后续开发。目标不是把项目做复杂，而是让三个人并行开发时边界清楚，后续功能扩展时不用推倒重写。

## 1. 总体原则

PetFlow 按五层组织：

```text
UI 层            tkinter 窗口、Canvas、Dialog
Application 层   用例服务、事件分发、ID 生成
Domain 层        节点、边、图模型、枚举、领域规则
Repository 层    JSON 保存和加载
Integration 层   Agent、剪贴板、前台窗口检测等外部能力
```

核心规则：

- UI 不直接操作文件。
- UI 不直接拼 LLM Prompt。
- UI 不绕过 `GraphService` 修改图数据。
- `Domain` 不依赖 Tkinter、requests、pywin32 或文件系统。
- `Agent` 返回的数据必须先校验和预览，再交给应用服务写入图。
- 系统能力都是选配模块，不能影响任务图基础功能启动。

## 2. 目录职责

```text
src/petflow/
  main.py                  程序入口
  config.py                路径和应用级配置
  domain/                  纯领域模型和规则
  app/                     应用服务、事件总线、用例编排
  repositories/            持久化接口和 JSON 实现
  services/                推荐、存储等业务服务
  ui/                      Tkinter 界面
  agent/                   LLM 客户端、Prompt、Agent 执行器
  system/                  剪贴板、前台窗口检测等系统集成
  models/                  兼容旧 import，新代码不要继续加内容
```

## 3. Domain 层

Domain 是项目地基，负责表达 PetFlow 的核心概念：

- `Node`：任务、Routine、资源、检查点、奖励。
- `Edge`：依赖、循环、推荐、触发。
- `GraphModel`：维护节点和边，执行结构性规则。
- `PetState`：桌宠当前节点、状态、位置、气泡文本。
- `WorkspaceState`：当前选中、缩放、平移、焦点模式等 UI 状态。

所有枚举放在 `domain/enums.py`，不要在代码里散落字符串，例如不要写 `"dependency"`、`"done"`，应使用：

```python
EdgeType.DEPENDENCY
NodeStatus.DONE
```

## 4. 图规则

图规则集中放在 `domain/rules.py` 和 `GraphModel` 中：

- Dependency 边不允许形成环。
- Routine、Recommendation、Trigger 边允许形成环。
- Edge 的 source 和 target 必须指向存在的节点。
- 删除节点时，关联边必须一起删除。
- 节点 ID 和边 ID 不允许重复。

以后新增规则时优先放到 Domain 层，而不是写在 Canvas 点击事件里。

Routine 的时间规则集中放在 `domain/routine.py`。状态流转由
`GraphService.update_node_status()` 统一处理：节点标记为 done 时写入完成时间；
Routine 节点同时更新 `last_completed_at`、`next_due_at` 和 `streak`。

推荐规则集中放在 `services/recommendation_engine.py`。推荐引擎必须遵守 Dependency
前置完成规则，并跳过 done、blocked 节点；UI 只能请求推荐结果，不能在界面层自行实现推荐算法。

桌宠响应集中放在 `services/pet_service.py` 和 `ui/pet_view.py`。`PetService`
负责监听图事件、更新 `PetState` 和发布 `PET_MOVED`；`PetView` 只负责在 Canvas
上绘制桌宠和气泡，不承载推荐或状态流转规则。

剪贴板捕获集中放在 `system/clipboard_watcher.py`。UI 负责读取桌面剪贴板内容，
`ClipboardWatcher` 只负责分类和生成捕获结果；写入任务图仍必须通过
`GraphService.create_resource_node()`。

附件路径通过 `GraphService.add_node_attachment()` 写入节点。UI 可以使用文件选择框
收集路径，但不能直接修改 `Node.attachments`。

## 5. Application 层

`GraphService` 是 UI 和 Agent 修改图的统一入口。

允许：

```python
graph_service.create_node(...)
graph_service.create_edge(...)
graph_service.update_node_status(...)
graph_service.move_node(...)
```

不建议：

```python
context.graph.nodes[node_id] = node
context.graph.edges[edge_id] = edge
```

原因是 `GraphService` 会统一处理 ID、事件、历史记录和未来的撤销重做逻辑。

后续扩展继续遵守一个原则：如果功能会改变任务图、工作区状态、历史记录或桌宠状态，
应先进入 Application 层或 Service 层，而不是直接写在 Tkinter 回调里。

当前建议新增或强化这些服务边界：

- `GraphLayoutService`：负责自动排列节点、整理 Agent 生成的子图、计算新节点默认位置。
- `RoutineService`：负责 Routine 到期查询、过期高亮、下次到期时间预览和批量刷新。
- `ReviewService`：负责根据 `history`、节点状态和 Routine 记录生成日/周复盘数据。
- `FocusService`：负责把前台窗口检测结果、专注计时和任务状态衔接起来。
- `ResourceService`：负责资源节点打开、复制、预览和附件列表展示所需的数据整理。

这些服务不必一次性全部创建。只有当对应功能开始变复杂时，才从 UI 或现有服务中抽出。
判断标准是：同一段业务逻辑被多个 UI 入口使用，或者它需要被单元测试稳定覆盖。

## 6. EventBus 设计

事件用于解耦模块：

- UI 修改节点后发布 `NODE_UPDATED`
- 推荐结果准备好后发布 `RECOMMENDATION_READY`
- 剪贴板捕获后发布 `CLIPBOARD_CAPTURED`
- 桌宠移动后发布 `PET_MOVED`

目前事件总线是同步实现，后期如有需要可以换成异步队列。业务模块之间不要互相直接调用复杂逻辑，优先通过服务或事件衔接。

## 7. 持久化规范

项目文件使用 JSON，默认路径为：

```text
data/graph.json
```

读写统一通过：

```python
StorageService
JsonGraphRepository
```

不要在 UI 代码里直接 `open()` 写 JSON。这样以后支持“另存为”“导入 Agent 结果”“导出演示样例”时不会扩散改动。

## 8. Agent 规范

Agent 模块分三部分：

- `PromptBuilder`：只负责生成 Prompt。
- `AgentClient`：只负责请求模型。
- `AgentExecutor`：只负责把已确认的 JSON proposal 应用到图。

Agent 的输出格式必须先经过这些步骤：

```text
LLM 原始输出 -> JSON 解析 -> 字段校验 -> 用户预览确认 -> GraphService 写入
```

Agent 不允许直接改 `GraphModel`。

Agent API 设置保存在本地 `data/settings.json`，该文件被 `.gitignore` 忽略，
不能提交到仓库。运行时优先读取本地设置；如果没有配置 API Key，则回退读取
`PETFLOW_AGENT_API_KEY` 或 `IMAGE_API_KEY` 环境变量；仍未配置时使用 mock 模式。

下一阶段 Agent 扩展重点不是让 Agent 直接拥有更多权限，而是让输入上下文和预览结果更可靠：

- 拆分节点时，Prompt 应包含当前节点描述、前置依赖、后置节点、已有标签和预计耗时。
- 生成任务图时，Prompt 应要求返回稳定字段，并给出简单布局坐标或层级关系。
- 复盘功能应先由本地 `ReviewService` 生成结构化统计，再交给 LLM 改写成自然语言。
- Agent 预览应优先展示结构化列表；JSON 原文可以保留为调试视图。
- `AgentExecutor` 仍然只能通过 `GraphService` 写入图，不能绕过成环检测和字段校验。

## 9. Python 环境规范

团队统一使用 Conda 环境 `petflow`，Python 版本固定在 3.12。当前项目不建议使用 Python 3.13，因为 macOS 下 Python 3.13 与系统 Tcl/Tk 组合可能出现 Tk 启动异常。

开发前先创建虚拟环境：

```bash
conda env create -f environment.yml
conda activate petflow
```

核心规则测试使用标准库 `unittest`，不依赖 pytest：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## 10. UI 规范

Tkinter UI 的职责是显示和收集用户操作。

`GraphCanvas` 负责：

- 绘制节点和边
- 处理拖拽、选择、右键菜单
- 把用户操作转成 `GraphService` 调用

Dialog 负责：

- 输入节点信息
- 输入边类型
- 展示 Agent 预览
- 展示错误提示

UI 里可以维护 Canvas item id 到 node id 的映射，但不能把业务规则写死在绘图代码里。

下一阶段 UI 打磨按“可演示、可理解、可恢复”的顺序推进：

- `GraphCanvas` 增加缩放、平移、整理布局和更清晰的边选中反馈。
- 节点详情界面补齐 Resource、Checklist、附件、实际耗时和标签等已有字段。
- Routine 节点需要有到期状态的视觉提示，而不是只在编辑框里显示 `next_due_at`。
- Agent 预览窗口从纯 JSON 文本升级为节点列表和边列表，保留 JSON 调试入口。
- 桌宠动画保持轻量，但状态变化要明确：推荐、完成、到期、专注偏离分别有不同气泡。
- 演示样例图必须能覆盖主要功能，不应依赖现场从零创建大量节点。

## 11. 三人协作边界

推荐分工：

- 组员 A：`domain/`、`repositories/`、`services/recommendation_engine.py`
- 组员 B：`ui/`，尤其是 `GraphCanvas` 和 Dialog
- 组员 C：`agent/`、`system/`、桌宠相关 UI

协作要求：

- 新增节点或边字段时，必须同步更新 `to_dict()` 和 `from_dict()`。
- 新增状态、类型时，必须先加枚举。
- UI 功能需要改图时，先看 `GraphService` 有没有方法；没有就补服务方法。
- 不要在同一个文件里堆多个不相关功能。

## 12. 当前框架支持的长期功能

当前框架已经为这些后续功能留好位置：

- 节点类型扩展：Task、Routine、Resource、Checkpoint、Reward。
- 边类型扩展：Dependency、Routine、Recommendation、Trigger。
- Routine 到期计算。
- Dependency 成环检测。
- 图内桌宠和未来悬浮桌宠。
- 本地推荐和 LLM 推荐解释。
- Agent 生成任务图和节点拆分。
- 剪贴板资源节点。
- 前台窗口检测和专注模式。
- 保存加载、导入导出、后续撤销重做。

## 13. 当前扩展路线

当前项目已经具备任务图、持久化、推荐、桌宠基础响应、Agent 生成/拆分和系统增强入口。
后续不建议重写框架，重点是把已有骨架打磨成完整体验。

优先级从高到低：

1. 图编辑体验：缩放、平移、布局整理、边选择反馈、节点多时的可读性。
2. 节点详情：资源打开/复制、附件展示、Checklist、标签、实际耗时。
3. Routine 闭环：到期查询、过期高亮、下一次到期预览、Routine 推荐解释。
4. Agent 体验：更丰富上下文、结构化预览、复盘入口、本地统计加 LLM 改写。
5. 桌宠体验：状态机、轻量动画、Routine 到期提醒、专注模式提示。
6. 系统增强：剪贴板定时检测、FocusMonitor 接入、演示数据和报告一致性。

如果时间不足，必须优先保证任务图编辑、保存加载、依赖规则、推荐和桌宠响应稳定。
专注模式、悬浮桌宠、复杂动画和文件拖拽都可以作为选做项。
