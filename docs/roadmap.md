# PetFlow 开发路线图

本文档描述从当前可运行框架继续扩展到最终演示版本的开发路径。目标是让三名组员可以按阶段并行推进，同时保证每一步都有清晰的验收标准。

后续开发必须遵守 `docs/architecture.md` 和 `docs/development.md` 中的模块边界。新增功能优先通过 `GraphService`、业务服务和事件机制接入，不把业务规则堆在 Tkinter 回调里。

## 1. 当前状态

当前项目已经完成一个可演示的基础闭环：

- Python 3.12 + Conda 环境。
- `domain / app / repositories / services / ui / agent / system` 分层。
- JSON 仓储、图模型、枚举、Dependency 成环检测。
- Tkinter 主窗口、工具栏、Canvas 节点和边绘制。
- 节点创建、编辑、删除、拖拽、状态切换。
- 边创建、编辑、删除，支持 Dependency / Routine / Recommendation / Trigger。
- 保存、加载和样例图入口。
- 本地推荐算法，支持依赖检查、优先级、doing、Routine 到期加权。
- 图内桌宠、气泡和完成任务后的推荐响应。
- Agent 生成任务图、拆分节点、JSON 预览、mock/API 双路径。
- 剪贴板捕获、文件附件入口、Focus Mode 开关和状态栏。
- 核心单元测试覆盖图模型、图服务、存储、推荐、Agent 和系统工具。

因此，后续路线不再是“搭框架”，而是“打磨体验闭环”。优先补齐用户能感知到的功能完整度，再做选做增强。

## 2. 总体策略

开发主线调整为：

```text
图编辑更好用 -> 节点详情更完整 -> Routine 可见可用 -> Agent 更可信 -> 桌宠更有响应 -> 系统增强和演示收口
```

优先级原则：

- 先稳定主流程：创建图、编辑图、保存加载、推荐、桌宠响应。
- 再补齐已有字段的 UI：资源、附件、Checklist、标签、实际耗时。
- Agent 和系统检测必须保留 mock 或降级路径，不能让网络或平台能力影响演示。
- 复杂动画、桌面悬浮宠物、文件拖拽和跨平台前台窗口检测都作为选做项。

## 3. 里程碑总览

```text
M0-M6 基础框架和 MVP          已基本完成
M7 图编辑体验打磨             缩放、平移、布局整理、边选择反馈
M8 节点详情和资源闭环          Resource、附件、Checklist、标签、实际耗时
M9 Routine 和推荐闭环          到期视图、过期高亮、推荐解释、状态刷新
M10 Agent 体验升级             更强 Prompt、结构化预览、复盘功能
M11 桌宠和专注模式增强          状态机、轻量动画、到期提醒、专注偏离提示
M12 最终演示和报告收口          样例数据、演示脚本、测试、文档一致性
```

建议优先完成 M7 到 M10。M11 是项目特色增强，M12 是提交前必须完成的收口阶段。

## 4. M7：图编辑体验打磨

### 目标

让任务图在节点数量变多时仍然可读、可操作、可演示。

### 主要任务

#### 组员 A：布局服务和工作区状态

- 设计 `GraphLayoutService` 或在应用层提供布局方法。
- 支持简单横向/网格排列节点。
- Agent 生成图和拆分节点后，能自动给出不重叠坐标。
- 保存和恢复 `WorkspaceState.zoom`、`pan_x`、`pan_y`。

#### 组员 B：Canvas 操作体验

- 实现基础缩放和平移。
- 优化边的选中区域和选中样式。
- 增加“整理布局”按钮。
- 拖拽节点时保持边实时刷新，并避免拖到不可见负坐标区域。
- 空图提示和边创建模式提示更明确。

#### 组员 C：演示样例图

- 准备一个覆盖主要功能的 `data/sample_graph.json`。
- 样例图至少包含 Task、Routine、Resource 三类节点。
- 样例图至少包含 Dependency 和 Routine 两类边。
- 节点坐标应适合首次打开窗口展示。

### 验收标准

- 能缩放和平移画布。
- 10 个以上节点时，用户可以整理布局并继续看清边关系。
- 边可以稳定选中、编辑和删除。
- 加载样例图后，第一屏能展示项目核心概念。

### 推荐提交

```text
feat: improve graph canvas navigation and layout
```

## 5. M8：节点详情和资源闭环

### 目标

让 `Node` 中已有字段真正可见、可编辑、可演示，尤其是 Resource、附件和 Checklist。

### 主要任务

#### 组员 A：节点字段服务方法

- 在 `GraphService` 中补充资源、标签、Checklist、实际耗时相关方法。
- 不允许 UI 直接修改 `Node.tags`、`Node.checklist`、`Node.resource_path`。
- 为新增方法补充单元测试。

#### 组员 B：节点详情 UI

- 扩展 `NodeDialog` 或新增详情面板。
- 支持编辑：
  - tags
  - actual_minutes
  - resource_type
  - resource_path
  - checklist
- 附件列表不只显示前三个，应能查看完整列表。
- Resource 节点提供打开链接、复制内容或打开文件路径的按钮。

#### 组员 C：剪贴板和附件体验

- 剪贴板捕获后，Resource 节点标题和描述更清晰。
- URL 资源写入 `resource_path`，文本资源写入描述或 metadata。
- 附件添加后在详情界面立即可见。

### 验收标准

- Resource 节点能展示并打开/复制资源。
- 节点能维护标签、实际耗时和 Checklist。
- 附件列表保存加载后不丢失。
- 相关字段的 JSON 序列化和反序列化测试通过。

### 推荐提交

```text
feat: complete node details and resource workflow
```

## 6. M9：Routine 和推荐闭环

### 目标

让 Routine 不只是一个节点类型，而是能被用户看到、完成、刷新和推荐的周期任务。

### 主要任务

#### 组员 A：RoutineService

- 新增或强化 Routine 查询逻辑。
- 提供 due / overdue / upcoming 的判断方法。
- 支持按到期时间返回 Routine 列表。
- 完成 Routine 后刷新 `last_completed_at`、`next_due_at`、`streak`。
- 覆盖 daily、weekly、monthly 的关键测试。

#### 组员 B：Routine UI

- Routine 节点在 Canvas 上显示到期状态。
- 到期或过期 Routine 使用额外标识，不只靠节点颜色。
- 状态栏或侧边栏展示“当前到期 Routine”。
- 编辑 Routine 时校验 `next_due_at` 格式，错误要提示。

#### 组员 C：推荐解释

- 推荐结果除了节点标题，还显示原因：
  - 前置依赖已完成
  - 优先级较高
  - Routine 已到期
  - 当前正在进行
- 推荐理由先用本地模板实现，LLM 改写作为选做。

### 验收标准

- 到期 Routine 能被视觉标识。
- 完成 Routine 后，下次到期时间和 streak 正确更新。
- 推荐节点时能展示一条本地推荐理由。
- blocked 和未满足依赖的节点不会被推荐。

### 推荐提交

```text
feat: add routine due workflow and recommendation reasons
```

## 7. M10：Agent 体验升级

### 目标

让 Agent 结果更可信、更可控、更适合演示，而不是只展示 JSON。

### 主要任务

#### 组员 A：Agent 校验和执行

- 校验 proposal 内部是否有重复临时 ID。
- 依赖边成环时给出明确错误。
- 对 Agent 生成节点数量设置合理上限，避免一次生成过多节点。
- `AgentExecutor` 保持只通过 `GraphService` 落图。

#### 组员 B：结构化预览

- `AgentDialog` 增加结构化预览：
  - 节点列表
  - 边列表
  - 预计新增数量
  - 可能的校验问题
- JSON 原文保留为调试视图或折叠区域。
- 应用后自动整理新节点布局并选中新增区域中的第一个节点。

#### 组员 C：Prompt 和复盘

- 拆分节点 Prompt 加入：
  - 当前节点标题和描述
  - 前置依赖
  - 后置节点
  - 预计耗时
  - 当前图中已有节点数量
- 生成任务图 Prompt 要求返回 3 到 10 个节点，避免结果过大。
- 新增复盘入口：先用本地统计生成 summary，再调用 Agent 改写。
- API 不可用时，用本地模板生成复盘。

### 验收标准

- Agent 生成和拆分结果能以结构化形式预览。
- 无 API Key 时 mock 模式仍可完整演示。
- 复盘功能至少能输出本地模板结果。
- Agent 返回异常 JSON 时不会破坏当前图。

### 推荐提交

```text
feat: improve agent previews and add review workflow
```

## 8. M11：桌宠和专注模式增强

### 目标

让桌宠从“会移动的装饰”提升为“任务图状态反馈入口”。

### 主要任务

#### 组员 A：事件和状态机

- 梳理桌宠状态转换：
  - idle：无推荐或空闲
  - think：用户请求推荐或 Agent 工作
  - happy：完成节点后推荐下一步
  - angry：专注模式偏离
  - sleep：长时间无操作
- 用事件驱动状态变化，避免 UI 直接写复杂桌宠逻辑。

#### 组员 B：PetView 动画

- 用 Canvas `after()` 实现轻量移动动画。
- 保持无图片资源时也能演示。
- 气泡文本自动截断，避免遮挡节点。
- 未来可以替换 PNG/GIF，但不作为主线阻塞。

#### 组员 C：Focus Mode

- Focus Mode 先实现稳定计时和当前任务提示。
- `FocusMonitor` 在 Windows 下使用 pywin32；其他平台返回 mock 或不可用状态。
- 检测到偏离时，桌宠提示用户回到当前节点。
- 是否创建 Reward/Distraction 节点作为选做，不放在主流程。

### 验收标准

- 完成任务、推荐任务、Routine 到期和专注偏离能触发不同气泡。
- 桌宠移动有基础动画，而不是瞬移。
- Focus Mode 在无 pywin32 的环境下不影响程序启动。
- 所有系统增强都有降级路径。

### 推荐提交

```text
feat: enhance pet reactions and focus mode
```

## 9. M12：最终演示和报告收口

### 目标

把项目整理成可以稳定提交、稳定演示、和文档一致的版本。

### 主要任务

- 运行完整测试：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

- 检查启动命令：

```bash
PYTHONPATH=src python -m petflow.main
```

- 准备最终 `data/sample_graph.json`。
- README 更新运行方式、功能清单和演示步骤。
- 报告中技术路线统一为 Python + Tkinter + Canvas。
- 删除或说明早期 Qt 方案只作为历史创意参考。
- 检查本地 `data/settings.json` 不被提交。
- 确认无 API Key 时 Agent mock 演示可用。

### 最终验收清单

- 环境能创建：`conda env create -f environment.yml`
- 程序能启动。
- 单元测试通过。
- 能创建、编辑、删除节点。
- 能拖拽节点。
- 能创建、编辑、删除边。
- Dependency 成环会被拒绝。
- Routine 环允许创建。
- JSON 保存和加载正确。
- 至少三种节点类型可见：Task、Routine、Resource。
- 至少两种边类型可见：Dependency、Routine。
- 能切换节点状态。
- 能推荐下一步并展示推荐理由。
- Routine 到期状态可见。
- 桌宠能响应节点完成和推荐。
- Agent 生成任务图或 mock 生成任务图可演示。
- Agent 拆分节点可演示。
- 剪贴板资源节点或附件功能可演示。
- 有演示样例数据。
- 文档、报告和实际功能一致。

## 10. 推荐演示路线

演示不要从空讲概念开始，直接操作软件：

1. 打开 PetFlow，加载示例任务图。
2. 展示 Task、Routine、Resource 三类节点。
3. 拖动节点，缩放和平移画布。
4. 创建一个 Dependency 边。
5. 尝试创建 Dependency 环，展示系统拒绝。
6. 创建 Routine 环，展示系统允许。
7. 标记一个节点为 done，展示推荐节点和推荐理由变化。
8. 桌宠移动到推荐节点旁并显示气泡。
9. 打开 Agent 窗口，输入课程大作业目标。
10. 展示 Agent 结构化预览。
11. 应用 Agent 结果并整理布局。
12. 对一个复杂节点执行拆分。
13. 展示 Resource 节点、剪贴板捕获或附件。
14. 展示 Focus Mode 或复盘功能作为加分项。
15. 保存、关闭、重新加载，展示持久化。

## 11. 风险控制

### 风险一：Canvas 交互耗时过长

先做缩放、平移和整理布局三个最有演示价值的操作。复杂手势、框选、多选和自动避障可以后置。

### 风险二：节点详情范围膨胀

优先把已有字段做成可见可保存。高级富文本、复杂附件管理和文件拖拽都作为选做项。

### 风险三：Agent API 不稳定

必须保留 mock 模式和本地模板。演示时不能依赖网络或 API Key。

### 风险四：桌宠动画成本高

桌宠核心价值是“响应任务图状态”。动画只做轻量移动和气泡变化，不追求复杂美术。

### 风险五：系统检测跨平台复杂

Focus Mode 先做 UI、计时和 mock 提示。前台窗口检测作为 Windows 加分项，不放在主线。

### 风险六：多人修改冲突

严格按模块分工。涉及公共领域模型的改动，先同步字段和 JSON 结构，再分别开发 UI 或 Agent。

## 12. 建议时间分配

如果总开发时间较紧，可以按比例分配：

```text
25%  图编辑体验和布局
20%  节点详情、资源和 Routine
20%  Agent 预览和复盘
15%  桌宠和专注模式
20%  测试、样例数据、UI 打磨、报告和演示
```

如果时间不足，优先砍选做功能，不能砍任务图编辑、保存加载、依赖规则、推荐理由、桌宠响应和 Agent mock 演示。
