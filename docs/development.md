# PetFlow 协作开发规范

本文档用于约束日常开发流程。所有组员在写功能前先阅读本文档、`docs/architecture.md` 和 `docs/roadmap.md`。

本文档的目标是：把当前已经能运行的代码作为 `main` 分支基线，之后所有开发都围绕这个基线做增量改动、测试和合并。

## 1. 环境搭建

推荐使用 Conda，并统一环境名为 `petflow`。

```bash
conda env create -f environment.yml
conda activate petflow
```

如果环境已经存在，可以更新：

```bash
conda env update -f environment.yml --prune
conda activate petflow
```

本机已验证的环境：

```text
Python 3.12.13
Tk 8.6
requests / Pillow import OK
compileall OK
unittest OK
```

推荐提交前保持这些检查都通过。

## 2. 运行项目

开发阶段使用源码目录运行：

```bash
PYTHONPATH=src python -m petflow.main
```

也可以用 Conda 直接运行：

```bash
conda run -n petflow env PYTHONPATH=src python -m petflow.main
```

如果在自动化终端或远程会话中测试 Tkinter，窗口探针可能因为没有正常的图形会话而挂起。GUI 功能优先在本机桌面终端里手动运行上面的命令验证。

当前项目的启动入口就是这一条，不要再回到旧的 Qt 或 Web 方案。

## 3. 验证命令

每次提交前至少执行：

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests
```

如果安装了 ruff，可以执行：

```bash
ruff check src tests
```

建议合并前至少完成：

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests
```

## 4. 分支规范

建议每个人在自己的功能分支上开发：

```text
feature/graph-canvas
feature/node-dialog
feature/agent-client
feature/pet-animation
fix/storage-load
docs/dev-guide
```

不要直接在主分支上堆多个无关功能。一个分支只解决一个清晰目标。

推荐的 GitHub 协作方式：

- `main` 只接收可运行、可测试、文档同步后的代码。
- 每个功能先开 Issue，再开分支，再提 PR。
- 一个 PR 只解决一类问题，避免同时改业务、UI、样例数据和文档。
- 合并前至少有一名其他组员 review。

## 5. 提交信息规范

提交信息建议使用：

```text
type: summary
```

常用 type：

```text
feat     新功能
fix      修复 bug
docs     文档
refactor 重构
test     测试
chore    工程配置
```

示例：

```text
feat: add node drag support
fix: reject dependency cycle
docs: add conda setup guide
```

## 6. 模块协作边界

### 组员 A：领域模型与存储

主要负责：

- `src/petflow/domain/`
- `src/petflow/repositories/`
- `src/petflow/services/recommendation_engine.py`
- `tests/`

注意事项：

- 新增字段必须同步更新 `to_dict()` 和 `from_dict()`。
- 新增类型必须先加枚举，不要散落字符串。
- 图规则优先写测试。

适合处理的工作：

- 节点/边字段变更
- Routine 规则
- 推荐算法
- JSON 兼容和存储
- 相关测试

### 组员 B：UI 与图编辑

主要负责：

- `src/petflow/ui/main_window.py`
- `src/petflow/ui/graph_canvas.py`
- 后续 Dialog 文件

注意事项：

- UI 修改图必须通过 `GraphService`。
- Canvas 中只保存绘图状态，不写业务规则。
- 复杂弹窗单独拆文件，不要全塞进 `main_window.py`。

适合处理的工作：

- Canvas 交互
- 节点/边编辑界面
- 样例图展示
- 工具栏和状态栏体验
- 与图编辑相关的 UI 打磨

### 组员 C：Agent、桌宠与系统能力

主要负责：

- `src/petflow/agent/`
- `src/petflow/system/`
- 后续桌宠 UI 组件

注意事项：

- Agent 不直接改 `GraphModel`。
- LLM 输出必须先预览和校验。
- 剪贴板和前台窗口检测不能影响主程序启动。

适合处理的工作：

- Agent 预览和应用
- mock / API 降级
- 桌宠绘制和状态响应
- Focus Mode
- 剪贴板与资源入口

## 7. 开发流程

推荐流程：

```text
阅读相关文档 -> 开分支 -> 写最小可用实现 -> 补测试或手动验证 -> 更新文档 -> 合并
```

每次开始写代码前先确认：

- 要改哪个模块？
- 是否会影响其他组员的文件？
- 是否需要新增领域规则？
- 是否需要更新 JSON 格式？
- 是否需要写测试？

建议每个任务都遵循这个最小闭环：

1. 先在 Issue 里说清楚目标和影响文件。
2. 分支只做这一件事。
3. 改代码时尽量先改服务层，再改 UI。
4. 补测试。
5. 更新相关文档或样例数据。
6. 提 PR，等 review 后合并。

## 8. 代码风格

- 使用 Python 类型标注。
- 函数尽量短，职责单一。
- 不在 UI 代码里写文件读写、网络请求或复杂图规则。
- 不在领域层 import Tkinter、requests、pywin32。
- 变量名使用英文，界面显示文本可以使用中文。
- 注释只解释不明显的业务规则，不重复代码表面含义。

## 9. JSON 兼容策略

项目文件默认保存在：

```text
data/graph.json
```

JSON 顶层字段包括：

```text
version
metadata
nodes
edges
pet
workspace
history
```

后续如果修改 JSON 结构，必须：

- 保留旧字段读取兼容。
- 更新 `docs/architecture.md` 或设计文档。
- 增加或更新测试。

目前仓库中的 `data/sample_graph.json` 和 `data/graph.json` 都属于项目基线数据。改动它们时要特别谨慎，因为它们会直接影响演示和回归测试。

## 10. 合并前检查清单

提交前自查：

- 程序能启动。
- 单元测试通过。
- 没有把 `.DS_Store`、临时 JSON、缓存文件提交进去。
- 没有把 API Key 写进代码。
- 没有绕过 `GraphService` 修改图数据。
- 新增模块有清楚的职责边界。

补充一条：如果改了 UI 但没有手动验证基本交互，就不要合并。至少确认以下动作可用：

- 打开程序
- 加载样例图
- 新建节点
- 编辑节点
- 创建和删除边
- 保存并重新加载
