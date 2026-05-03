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
